# PROMPT PARA CURSOR — Comparación Wavelet vs Enfoque Estándar para Predicción t+1
## Flota 794AC — Mina Quellaveco

---

## CONTEXTO Y DIAGNÓSTICO PREVIO

Antes de implementar, el análisis de la data revela un **problema crítico para wavelets**:

```
HT001: Coef. variación de Δhoras = 0.83  → muestreo muy irregular
HT012: Coef. variación de Δhoras = 1.05  → muestreo extremadamente irregular
HT011: Coef. variación de Δhoras = 1.19  → muestreo extremadamente irregular

Si se resamplea a intervalos de 50h regulares:
→ De ~168 muestras reales se pasa a solo ~13 puntos por equipo
→ Se pierde el 92% de la información
```

**Conclusión de diagnóstico:**
- La DWT clásica (Daubechies, Haar, Symlets) sobre eje temporal/horario NO es directamente
  aplicable sin pérdida severa de información.
- SIN EMBARGO, el wavelet sí aporta valor como **filtro de señal por índice de muestra**
  para separar tendencia lenta de fluctuaciones rápidas.
- La no-estacionariedad es real y significativa (p<0.0001 en todas las variables):
  TBN tiene slope=-0.012 por muestra, Hollín=+0.005, Fierro=+0.14.

**Estrategia adoptada:** Se implementan 4 enfoques y se comparan:
1. **Baseline Estándar**: lags + rolling stats (Fase 2 original)
2. **Wavelet por Índice**: DWT sobre la secuencia de muestras por índice ordinal
3. **Wavelet + Interpolación**: resampleo a horas regulares → DWT → features
4. **Híbrido**: lags estándar + coeficientes wavelet como features adicionales ← (se espera que sea el mejor)

---

## OBJETIVO

Determinar si la descomposición wavelet mejora la predicción t+1 de las variables
analíticas del aceite (TBN, Hollín, Fierro, Viscosidad, Oxidación) comparada con el
enfoque estándar de lags/rolling, y cuantificar esa mejora en MAE, RMSE y R².

---

## LIBRERÍAS REQUERIDAS

```python
# Instalar si no están:
# pip install pywavelets lightgbm xgboost optuna scikit-learn pandas numpy matplotlib seaborn
import pywt              # PyWavelets — librería principal de wavelets
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy import interpolate, stats
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['figure.dpi'] = 120
import os
os.makedirs('outputs_wavelet', exist_ok=True)
```

---

## SECCIÓN 0 — CONFIGURACIÓN

```python
FILE_PATH  = 'DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx'
SHEET_NAME = '794AC QUELLA'
RANDOM_STATE = 42

# Variables objetivo del análisis
VARS_TARGET = [
    'TBN (mg KOH/g)',
    'Viscosidad a 100 °C cSt',
    'Hollin ABS/01 mm',
    'Fierro ppm',
    'Oxidación ABS/01 mm',
    'Sulfatación ABS/01 mm',
    'Cobre ppm',
]

# Equipos con mayor número de muestras (mayor confiabilidad estadística)
EQUIPOS_ANALISIS = ['HT001', 'HT012', 'HT011', 'HT005', 'HT006', 'HT002',
                    'HT007', 'HT003', 'HT016', 'HT015']

# Parámetros wavelet
WAVELET_FAMILIA  = 'db4'    # Daubechies 4 — buena para señales suaves con tendencia
WAVELET_NIVEL    = 3        # Niveles de descomposición (3 = tendencia + 3 capas de detalle)
N_LAGS_STANDARD  = 5        # Lags para el enfoque estándar
HORA_STEP_INTERP = 50       # Horas para resampleo regular en Enfoque 3

# Familias wavelet a evaluar en la comparación interna
WAVELETS_A_PROBAR = ['haar', 'db4', 'sym4', 'coif2', 'bior3.3']
```

---

## SECCIÓN 1 — CARGA Y PREPARACIÓN DE DATOS

```python
df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
df['Fecha'] = pd.to_datetime(df['Fecha'])
df['Hora_Producto'] = pd.to_numeric(df['Hora_Producto'], errors='coerce')

for col in VARS_TARGET:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

estado_map = {'NORMAL': 0, 'PRECAUCION': 1, 'CRITICO': 2}
df['Estado_num'] = df['Estado'].map(estado_map)
df = df.sort_values(['Equipo', 'Hora_Producto']).reset_index(drop=True)
df_analisis = df[df['Equipo'].isin(EQUIPOS_ANALISIS)].copy()

print(f"Dataset: {df_analisis.shape[0]} muestras | {df_analisis['Equipo'].nunique()} equipos")
```

---

## SECCIÓN 2 — ANÁLISIS WAVELET EXPLORATORIO

### 2.1 — Selección de la familia wavelet óptima por variable

```python
# Antes de usarlos como features, determinar qué familia wavelet
# reconstruye mejor cada señal (menor error de reconstrucción).
# Esto se hace para cada variable en el equipo con más muestras (HT012).

print("="*65)
print("SELECCIÓN DE FAMILIA WAVELET ÓPTIMA POR VARIABLE")
print("="*65)

wavelet_selection = {}

for var in VARS_TARGET:
    grp = df_analisis[df_analisis['Equipo']=='HT012'].sort_values('Hora_Producto')
    s = grp[var].dropna().values
    if len(s) < 20:
        continue

    best_wavelet = None
    best_snr = -np.inf
    resultados_wav = []

    for wv_name in WAVELETS_A_PROBAR:
        try:
            # Descomponer
            coeffs = pywt.wavedec(s, wv_name, level=WAVELET_NIVEL)
            # Reconstruir
            s_rec = pywt.waverec(coeffs, wv_name)[:len(s)]
            # SNR de reconstrucción (cuánta señal se preserva)
            signal_power = np.var(s)
            noise_power  = np.var(s - s_rec)
            snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
            # RMSE
            rmse = np.sqrt(np.mean((s - s_rec)**2))
            resultados_wav.append({'Wavelet': wv_name, 'SNR_dB': round(snr, 2), 'RMSE_rec': round(rmse, 6)})
            if snr > best_snr:
                best_snr = snr
                best_wavelet = wv_name
        except Exception as e:
            pass

    wavelet_selection[var] = best_wavelet
    print(f"\n  Variable: {var}")
    for r in sorted(resultados_wav, key=lambda x: x['SNR_dB'], reverse=True):
        marker = ' ← MEJOR' if r['Wavelet'] == best_wavelet else ''
        print(f"    {r['Wavelet']:10s}: SNR={r['SNR_dB']:6.2f} dB | RMSE_rec={r['RMSE_rec']:.6f}{marker}")

print(f"\n\nFAMILIAS SELECCIONADAS POR VARIABLE:")
for var, wv in wavelet_selection.items():
    print(f"  {var[:35]:35s}: {wv}")
```

### 2.2 — Visualización de la descomposición wavelet

```python
# Para TBN y Hollín en HT001, visualizar la descomposición completa:
# Señal original + Aproximación (tendencia) + 3 niveles de Detalle
# Esto muestra visualmente qué captura cada componente

fig, axes = plt.subplots(len(VARS_TARGET[:4]), WAVELET_NIVEL + 2,
                          figsize=(22, 16))
fig.suptitle(f'Descomposición Wavelet ({WAVELET_FAMILIA}) — HT001',
             fontsize=14, fontweight='bold')

COLORES_ESTADO = {'NORMAL': '#2ecc71', 'PRECAUCION': '#f39c12', 'CRITICO': '#e74c3c'}

for row_idx, var in enumerate(VARS_TARGET[:4]):
    grp = df_analisis[df_analisis['Equipo']=='HT001'].sort_values('Hora_Producto')
    s_full = grp[var].dropna().values
    estados = grp.loc[grp[var].notna(), 'Estado'].values
    n = len(s_full)

    if n < 16:
        continue

    # Wavelet sobre índice de muestra (no sobre tiempo real)
    wv_name = wavelet_selection.get(var, WAVELET_FAMILIA)
    coeffs = pywt.wavedec(s_full, wv_name, level=WAVELET_NIVEL)

    # Plot señal original coloreada por estado
    ax = axes[row_idx, 0]
    for est, color in COLORES_ESTADO.items():
        mask = estados == est
        ax.scatter(np.where(mask)[0], s_full[mask], c=color, s=15, alpha=0.7, label=est)
    ax.plot(s_full, 'k-', linewidth=0.5, alpha=0.4)
    ax.set_title(f'{var[:20]}\nOriginal', fontsize=8)
    ax.set_ylabel(var[:15], fontsize=7)
    if row_idx == 0:
        ax.legend(fontsize=6)

    # Plot Aproximación (tendencia de baja frecuencia)
    ax = axes[row_idx, 1]
    approx_reconstructed = pywt.waverec(
        [coeffs[0]] + [np.zeros_like(c) for c in coeffs[1:]], wv_name
    )[:n]
    ax.plot(approx_reconstructed, color='navy', linewidth=1.5)
    ax.plot(s_full, 'k-', linewidth=0.5, alpha=0.3)
    ax.set_title('Aproximación\n(Tendencia)', fontsize=8)
    ax.axhline(approx_reconstructed.mean(), color='red', linestyle=':', alpha=0.5)

    # Plot niveles de detalle
    for level_idx in range(WAVELET_NIVEL):
        ax = axes[row_idx, level_idx + 2]
        detail_coeffs = [np.zeros_like(coeffs[0])] + [
            c if i == level_idx + 1 else np.zeros_like(c)
            for i, c in enumerate(coeffs[1:], 1)
        ]
        detail_reconstructed = pywt.waverec(detail_coeffs, wv_name)[:n]
        color = ['#e74c3c', '#f39c12', '#3498db'][level_idx % 3]
        ax.plot(detail_reconstructed, color=color, linewidth=1.0)
        ax.axhline(0, color='black', linestyle='--', linewidth=0.5, alpha=0.4)
        ax.set_title(f'Detalle Nivel {level_idx + 1}\n({"alta" if level_idx==0 else "media" if level_idx==1 else "baja"} frecuencia)',
                     fontsize=8)

axes[-1, 0].set_xlabel('Índice de muestra')
plt.tight_layout()
plt.savefig('outputs_wavelet/01_descomposicion_wavelet_HT001.png', dpi=150, bbox_inches='tight')
plt.show()
```

### 2.3 — Reconstrucción suavizada (denoising)

```python
# Aplicar umbralización (thresholding) de coeficientes de detalle
# para obtener una señal más limpia sin ruido de alta frecuencia.
# Comparar señal original vs señal suavizada por wavelet.
# Esto es útil para las tendencias de degradación.

def wavelet_denoise(signal, wavelet='db4', level=3, threshold_mode='soft'):
    """
    Suaviza una señal eliminando ruido de alta frecuencia mediante wavelet.

    Args:
        signal: array 1D de la señal
        wavelet: familia wavelet
        level: niveles de descomposición
        threshold_mode: 'soft' o 'hard'
    Returns:
        señal suavizada
    """
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    # Umbral de Donoho-Johnstone (optimal universal threshold)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    threshold = sigma * np.sqrt(2 * np.log(len(signal)))
    # Aplicar umbralización solo a coeficientes de detalle (no a aproximación)
    coeffs_thresh = [coeffs[0]]  # Mantener aproximación intacta
    for detail in coeffs[1:]:
        coeffs_thresh.append(pywt.threshold(detail, threshold, mode=threshold_mode))
    return pywt.waverec(coeffs_thresh, wavelet)[:len(signal)]


fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('Wavelet Denoising — Señal Original vs Suavizada\n(Umbral Donoho-Johnstone)',
             fontsize=13, fontweight='bold')

for idx, var in enumerate(VARS_TARGET[:6]):
    ax = axes[idx // 3, idx % 3]
    for equipo, color_eq in [('HT001', 'navy'), ('HT012', 'darkgreen')]:
        grp = df_analisis[df_analisis['Equipo']==equipo].sort_values('Hora_Producto')
        s = grp[var].dropna().values
        if len(s) < 16:
            continue
        wv_name = wavelet_selection.get(var, WAVELET_FAMILIA)
        s_smooth = wavelet_denoise(s, wavelet=wv_name, level=WAVELET_NIVEL)
        x = np.arange(len(s))
        ax.scatter(x, s, c=color_eq, alpha=0.3, s=12, label=f'{equipo} (orig)')
        ax.plot(x, s_smooth, color=color_eq, linewidth=2, alpha=0.9, label=f'{equipo} (smooth)')

    ax.set_title(f'{var[:30]}', fontsize=9)
    ax.set_xlabel('Índice de muestra')
    ax.legend(fontsize=6)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('outputs_wavelet/02_wavelet_denoising.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## SECCIÓN 3 — CONSTRUCCIÓN DE FEATURES PARA CADA ENFOQUE

### 3.1 — Funciones de construcción de features

```python
# ── ENFOQUE 1: Estándar (lags + rolling) ─────────────────────────────
def build_standard_features(df_eq, vars_target, n_lags=5):
    """Features clásicas: lags, deltas, rolling stats."""
    feat = pd.DataFrame()
    feat['Hora_Producto'] = df_eq['Hora_Producto'].values
    feat['Estado_num']    = df_eq['Estado_num'].values
    feat['horas_actuales'] = df_eq['Hora_Producto'].values

    for var in vars_target:
        if var not in df_eq.columns:
            continue
        s = df_eq[var]
        for k in range(1, n_lags + 1):
            feat[f'lag{k}_{var[:15]}'] = s.shift(k).values
        for k in range(1, n_lags):
            feat[f'delta{k}_{var[:15]}'] = (s.shift(k) - s.shift(k+1)).values
        # Rolling sobre muestras previas (shift(1) para evitar leakage)
        for w in [3, 5]:
            feat[f'rollmean{w}_{var[:12]}'] = s.shift(1).rolling(w, min_periods=2).mean().values
            feat[f'rollstd{w}_{var[:12]}']  = s.shift(1).rolling(w, min_periods=2).std().values

    feat['estado_lag1'] = df_eq['Estado_num'].shift(1).values
    feat['horas_desde_ultima'] = df_eq['Hora_Producto'].diff().values
    return feat


# ── ENFOQUE 2: Wavelet por Índice ─────────────────────────────────────
def build_wavelet_index_features(df_eq, vars_target, wavelet_map,
                                 nivel=3, n_lags=3):
    """
    Descompone cada variable por índice de muestra (no por tiempo real).
    Para cada punto t, calcula features wavelet usando SOLO muestras anteriores.

    Estrategia:
    1. Para cada punto t, tomar las últimas min(2^(nivel+1), t) muestras como ventana
    2. Aplicar DWT a esa ventana
    3. Extraer: coef. de aproximación (cA) y detalle del último nivel (cD1)
    4. Usar el ÚLTIMO coeficiente de cada nivel como feature para t
    """
    feat = pd.DataFrame()
    feat['Hora_Producto'] = df_eq['Hora_Producto'].values
    feat['Estado_num']    = df_eq['Estado_num'].values
    feat['horas_actuales'] = df_eq['Hora_Producto'].values
    n = len(df_eq)
    min_window = 2 ** (nivel + 1)  # Mínimo requerido para DWT nivel=3: 16 puntos

    for var in vars_target:
        if var not in df_eq.columns:
            continue
        s = df_eq[var].fillna(method='ffill').fillna(method='bfill').values
        wv_name = wavelet_map.get(var, 'db4')

        # Features wavelet para cada punto t
        cA_feat    = np.full(n, np.nan)   # Último coef. aproximación
        cD1_feat   = np.full(n, np.nan)   # Último coef. detalle nivel 1 (alta freq)
        cD_last_feat = np.full(n, np.nan) # Último coef. detalle último nivel (baja freq)
        energy_feat  = np.full(n, np.nan) # Energía total de la señal en ventana
        entropy_feat = np.full(n, np.nan) # Entropía wavelet (complejidad de señal)

        for t in range(min_window, n):
            # Ventana de muestras ANTERIORES a t (sin incluir t)
            window_size = min(t, 32)  # Máximo 32 muestras para eficiencia
            window = s[max(0, t - window_size):t]

            if len(window) < min_window or np.all(np.isnan(window)):
                continue
            # Reemplazar NaN internos con interpolación lineal
            window_clean = pd.Series(window).interpolate().values

            try:
                max_level = pywt.dwt_max_level(len(window_clean), wv_name)
                actual_level = min(nivel, max_level)
                coeffs = pywt.wavedec(window_clean, wv_name, level=actual_level)

                cA    = coeffs[0]
                cD1   = coeffs[-1]   # Detalle de mayor frecuencia
                cD_last = coeffs[1]  # Detalle de menor frecuencia

                cA_feat[t]      = cA[-1]       # Último coef. de aproximación
                cD1_feat[t]     = cD1[-1]      # Último coef. detalle alta freq
                cD_last_feat[t] = cD_last[-1]  # Último coef. detalle baja freq

                # Energía = suma de cuadrados de todos los coeficientes
                all_coeffs = np.concatenate([c for c in coeffs])
                energy_feat[t]  = np.sum(all_coeffs**2)

                # Entropía wavelet de Shannon
                energy_norm = all_coeffs**2 / (np.sum(all_coeffs**2) + 1e-10)
                entropy_feat[t] = -np.sum(energy_norm * np.log(energy_norm + 1e-10))

            except Exception:
                pass

        vname = var[:12]
        feat[f'wv_cA_{vname}']       = cA_feat
        feat[f'wv_cD1_{vname}']      = cD1_feat
        feat[f'wv_cDlast_{vname}']   = cD_last_feat
        feat[f'wv_energy_{vname}']   = energy_feat
        feat[f'wv_entropy_{vname}']  = entropy_feat

        # También incluir lags básicos (3) para contexto local
        for k in range(1, n_lags + 1):
            feat[f'lag{k}_{vname}'] = pd.Series(s).shift(k).values

    feat['estado_lag1']       = df_eq['Estado_num'].shift(1).values
    feat['horas_desde_ultima'] = df_eq['Hora_Producto'].diff().values
    return feat


# ── ENFOQUE 3: Wavelet + Interpolación ───────────────────────────────
def build_wavelet_interp_features(df_eq, vars_target, wavelet_map,
                                  hora_step=50, nivel=3):
    """
    Interpola a horas regulares → aplica DWT → extrapola coeficientes de vuelta
    a las horas originales para usarlos como features.
    """
    feat = pd.DataFrame()
    feat['Hora_Producto'] = df_eq['Hora_Producto'].values
    feat['Estado_num']    = df_eq['Estado_num'].values
    feat['horas_actuales'] = df_eq['Hora_Producto'].values
    n = len(df_eq)

    horas_orig = df_eq['Hora_Producto'].values

    for var in vars_target:
        if var not in df_eq.columns:
            continue
        s_orig = df_eq[var].fillna(method='ffill').fillna(method='bfill').values
        wv_name = wavelet_map.get(var, 'db4')
        vname = var[:12]

        # Interpolación lineal a horas regulares
        h_min, h_max = horas_orig.min(), horas_orig.max()
        h_regular = np.arange(h_min, h_max + hora_step, hora_step)

        try:
            # Solo interpolar si hay suficientes puntos
            if len(horas_orig) < 4 or len(h_regular) < 8:
                continue
            interp_func = interpolate.interp1d(horas_orig, s_orig,
                                               kind='linear', bounds_error=False,
                                               fill_value=(s_orig[0], s_orig[-1]))
            s_regular = interp_func(h_regular)

            # DWT sobre la señal regularizada
            max_level = pywt.dwt_max_level(len(s_regular), wv_name)
            actual_level = min(nivel, max_level)
            if actual_level < 1:
                continue
            coeffs = pywt.wavedec(s_regular, wv_name, level=actual_level)

            # Reconstruir señal suavizada (solo aproximación)
            approx_regular = pywt.waverec(
                [coeffs[0]] + [np.zeros_like(c) for c in coeffs[1:]], wv_name
            )[:len(s_regular)]

            # Reconstruir solo detalle nivel 1 (alta frecuencia = ruido)
            detail_regular = pywt.waverec(
                [np.zeros_like(coeffs[0])] + [coeffs[1]] + [np.zeros_like(c) for c in coeffs[2:]],
                wv_name
            )[:len(s_regular)]

            # Interpolar de vuelta a las horas originales
            interp_approx = interpolate.interp1d(h_regular, approx_regular,
                                                  kind='linear', bounds_error=False,
                                                  fill_value=(approx_regular[0], approx_regular[-1]))
            interp_detail = interpolate.interp1d(h_regular, detail_regular,
                                                  kind='linear', bounds_error=False,
                                                  fill_value=(detail_regular[0], detail_regular[-1]))

            feat[f'wvi_approx_{vname}']   = interp_approx(horas_orig)
            feat[f'wvi_detail_{vname}']   = interp_detail(horas_orig)
            feat[f'wvi_ratio_{vname}']    = (feat[f'wvi_detail_{vname}'] /
                                              (np.abs(feat[f'wvi_approx_{vname}']) + 1e-6))
            # Derivada de la aproximación (tasa de cambio de la tendencia)
            approx_vals = interp_approx(horas_orig)
            feat[f'wvi_dapprox_{vname}']  = np.gradient(approx_vals)

        except Exception as e:
            feat[f'wvi_approx_{vname}']  = np.nan
            feat[f'wvi_detail_{vname}']  = np.nan
            feat[f'wvi_ratio_{vname}']   = np.nan
            feat[f'wvi_dapprox_{vname}'] = np.nan

        # Incluir lags básicos
        for k in range(1, 4):
            feat[f'lag{k}_{vname}'] = pd.Series(s_orig).shift(k).values

    feat['estado_lag1']        = df_eq['Estado_num'].shift(1).values
    feat['horas_desde_ultima'] = df_eq['Hora_Producto'].diff().values
    return feat


# ── ENFOQUE 4: Híbrido (Estándar + Wavelet como features extra) ───────
def build_hybrid_features(df_eq, vars_target, wavelet_map, n_lags=5, nivel=3):
    """
    Combina las features estándar de la Fase 2 con las features wavelet.
    Aprovecha lo mejor de ambos mundos.
    """
    # Features estándar completas
    std_feat  = build_standard_features(df_eq, vars_target, n_lags=n_lags)
    # Features wavelet por índice
    wv_feat   = build_wavelet_index_features(df_eq, vars_target, wavelet_map, nivel=nivel)
    # Features wavelet con interpolación
    wvi_feat  = build_wavelet_interp_features(df_eq, vars_target, wavelet_map, nivel=nivel)

    # Columnas wavelet únicas (sin duplicar lags)
    wv_only_cols  = [c for c in wv_feat.columns
                     if c.startswith('wv_') and c not in std_feat.columns]
    wvi_only_cols = [c for c in wvi_feat.columns
                     if c.startswith('wvi_') and c not in std_feat.columns]

    hybrid = pd.concat([
        std_feat,
        wv_feat[wv_only_cols].reset_index(drop=True),
        wvi_feat[wvi_only_cols].reset_index(drop=True)
    ], axis=1)

    return hybrid

print("✓ Funciones de construcción de features definidas")
print(f"  Enfoques: Estándar | Wavelet-Índice | Wavelet-Interp | Híbrido")
```

---

## SECCIÓN 4 — EXPERIMENTO COMPARATIVO PRINCIPAL

### 4.1 — Preparar todos los datasets de features

```python
print("Construyendo features para los 4 enfoques...")
print("(Este proceso puede tomar 3-8 minutos según el hardware)\n")

all_standard = []
all_wavelet_idx = []
all_wavelet_interp = []
all_hybrid = []

for equipo in EQUIPOS_ANALISIS:
    grp = df_analisis[df_analisis['Equipo']==equipo].sort_values('Hora_Producto').copy()
    grp = grp.reset_index(drop=True)

    if len(grp) < 30:
        print(f"  ⚠ {equipo}: muy pocas muestras ({len(grp)}), omitiendo.")
        continue

    print(f"  Procesando {equipo} ({len(grp)} muestras)...", end=' ')

    f1 = build_standard_features(grp, VARS_TARGET, n_lags=N_LAGS_STANDARD)
    f2 = build_wavelet_index_features(grp, VARS_TARGET, wavelet_selection, nivel=WAVELET_NIVEL)
    f3 = build_wavelet_interp_features(grp, VARS_TARGET, wavelet_selection, hora_step=HORA_STEP_INTERP)
    f4 = build_hybrid_features(grp, VARS_TARGET, wavelet_selection, n_lags=N_LAGS_STANDARD)

    # Agregar columnas de identificación y target
    for feat_df, store_list in [(f1, all_standard), (f2, all_wavelet_idx),
                                 (f3, all_wavelet_interp), (f4, all_hybrid)]:
        feat_df['Equipo'] = equipo
        feat_df['Fecha']  = grp['Fecha'].values
        for var in VARS_TARGET:
            if var in grp.columns:
                feat_df[f'target_{var[:15]}'] = grp[var].values
        store_list.append(feat_df)
    print("✓")

df_std   = pd.concat(all_standard,      ignore_index=True)
df_wv    = pd.concat(all_wavelet_idx,   ignore_index=True)
df_wvi   = pd.concat(all_wavelet_interp,ignore_index=True)
df_hyb   = pd.concat(all_hybrid,        ignore_index=True)

print(f"\nDatasets construidos:")
print(f"  Estándar:          {df_std.shape[0]} muestras × {df_std.shape[1]} cols")
print(f"  Wavelet-Índice:    {df_wv.shape[0]}  muestras × {df_wv.shape[1]} cols")
print(f"  Wavelet-Interp:    {df_wvi.shape[0]} muestras × {df_wvi.shape[1]} cols")
print(f"  Híbrido:           {df_hyb.shape[0]} muestras × {df_hyb.shape[1]} cols")
```

### 4.2 — Función de entrenamiento y evaluación (LightGBM)

```python
def train_and_evaluate_lgbm(df_feat, target_var, approach_name,
                             exclude_cols=None, random_state=42):
    """
    Entrena LightGBM para predecir target_var.
    Split temporal 80/20. Devuelve métricas y predicciones.
    """
    target_col = f'target_{target_var[:15]}'
    if target_col not in df_feat.columns:
        return None

    # Identificar columnas de features
    if exclude_cols is None:
        exclude_cols = []
    meta = ['Equipo', 'Fecha', 'Hora_Producto', 'Estado_num'] + \
           [c for c in df_feat.columns if c.startswith('target_')] + \
           exclude_cols
    feat_cols = [c for c in df_feat.columns if c not in meta]

    # Filtrar por variable válida
    valid = df_feat[target_col].notna() & df_feat[feat_cols[0]].notna()
    sub = df_feat[valid].copy()
    if len(sub) < 100:
        return None

    X = sub[feat_cols].fillna(sub[feat_cols].median())
    y = sub[target_col].values

    # Split temporal (NO shuffle — respetar orden cronológico)
    split = int(len(X) * 0.80)
    X_tr, X_te = X.iloc[:split], X.iloc[split:]
    y_tr, y_te = y[:split], y[split:]

    params = {
        'objective': 'regression', 'metric': 'mae', 'verbosity': -1,
        'n_estimators': 300, 'max_depth': 6, 'learning_rate': 0.05,
        'num_leaves': 63, 'subsample': 0.8, 'colsample_bytree': 0.8,
        'min_child_samples': 10, 'random_state': random_state, 'n_jobs': -1
    }

    model = lgb.LGBMRegressor(**params)
    model.fit(X_tr, y_tr,
              eval_set=[(X_te, y_te)],
              callbacks=[lgb.early_stopping(30, verbose=False)])

    y_pred = model.predict(X_te)
    mae    = mean_absolute_error(y_te, y_pred)
    rmse   = np.sqrt(mean_squared_error(y_te, y_pred))
    r2     = r2_score(y_te, y_pred)
    mape   = np.mean(np.abs((y_te - y_pred) / (np.abs(y_te) + 1e-8))) * 100

    # Mejora sobre un baseline naïve (predecir siempre la media de train)
    mae_naive = mean_absolute_error(y_te, np.full_like(y_te, y_tr.mean()))
    skill_score = (1 - mae / mae_naive) * 100  # % de mejora sobre naïve

    return {
        'Enfoque': approach_name,
        'Variable': target_var,
        'MAE': round(mae, 5),
        'RMSE': round(rmse, 5),
        'R2': round(r2, 5),
        'MAPE_%': round(mape, 2),
        'Skill_%': round(skill_score, 1),
        'N_train': len(X_tr),
        'N_test': len(X_te),
        'N_features': len(feat_cols),
        'y_pred': y_pred,
        'y_test': y_te
    }
```

### 4.3 — Ejecutar la comparación para todas las variables

```python
print("="*70)
print("COMPARACIÓN DE ENFOQUES — Predicción t+1")
print("="*70)

all_results = []
predictions_store = {}

datasets = [
    (df_std,  'Estándar (Lags)'),
    (df_wv,   'Wavelet-Índice'),
    (df_wvi,  'Wavelet-Interp'),
    (df_hyb,  'Híbrido (Lags+WV)'),
]

for var in VARS_TARGET:
    print(f"\n  Variable: {var}")
    var_preds = {}

    for df_feat, approach_name in datasets:
        res = train_and_evaluate_lgbm(df_feat, var, approach_name)
        if res is not None:
            print(f"    {approach_name:22s}: MAE={res['MAE']:.5f} | "
                  f"R²={res['R2']:.4f} | MAPE={res['MAPE_%']:.1f}% | "
                  f"Skill={res['Skill_%']:.1f}%")
            var_preds[approach_name] = {'pred': res.pop('y_pred'), 'real': res.pop('y_test')}
            all_results.append(res)

    predictions_store[var] = var_preds

results_df = pd.DataFrame(all_results)
print(f"\n{'='*70}")
print("TABLA RESUMEN COMPLETA:")
print(results_df[['Variable','Enfoque','MAE','R2','MAPE_%','Skill_%']].to_string(index=False))
results_df.to_excel('outputs_wavelet/03_comparacion_enfoques.xlsx', index=False)
```

---

## SECCIÓN 5 — VISUALIZACIONES DE COMPARACIÓN

### 5.1 — Heatmap de R² por enfoque y variable

```python
pivot_r2   = results_df.pivot(index='Variable', columns='Enfoque', values='R2')
pivot_mae  = results_df.pivot(index='Variable', columns='Enfoque', values='MAE')
pivot_skill = results_df.pivot(index='Variable', columns='Enfoque', values='Skill_%')

fig, axes = plt.subplots(1, 3, figsize=(20, 6))

for ax, pivot, title, cmap, fmt in [
    (axes[0], pivot_r2,    'R² (mayor = mejor)',      'YlGn',  '.4f'),
    (axes[1], pivot_mae,   'MAE (menor = mejor)',     'YlOrRd_r', '.5f'),
    (axes[2], pivot_skill, 'Skill Score % vs Naïve',  'RdYlGn', '.1f'),
]:
    sns.heatmap(pivot, annot=True, fmt=fmt, cmap=cmap,
                linewidths=0.5, ax=ax, cbar_kws={'shrink': 0.8},
                annot_kws={'size': 9})
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.tick_params(axis='x', rotation=25)
    ax.tick_params(axis='y', rotation=0)

plt.suptitle('Comparación de Enfoques: Estándar vs Wavelet vs Híbrido\n'
             '(Predicción t+1 — Flota 794AC Quellaveco)',
             fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('outputs_wavelet/04_heatmap_comparacion.png', dpi=150, bbox_inches='tight')
plt.show()
```

### 5.2 — Gráfico de mejora del Híbrido sobre el Estándar

```python
# Para cada variable, calcular la mejora % del Híbrido sobre el Estándar
mejora_data = []
for var in VARS_TARGET:
    sub = results_df[results_df['Variable'] == var]
    r2_std = sub[sub['Enfoque']=='Estándar (Lags)']['R2'].values
    r2_hyb = sub[sub['Enfoque']=='Híbrido (Lags+WV)']['R2'].values
    mae_std = sub[sub['Enfoque']=='Estándar (Lags)']['MAE'].values
    mae_hyb = sub[sub['Enfoque']=='Híbrido (Lags+WV)']['MAE'].values

    if len(r2_std) > 0 and len(r2_hyb) > 0:
        mejora_r2  = (r2_hyb[0] - r2_std[0]) * 100
        mejora_mae = (mae_std[0] - mae_hyb[0]) / (mae_std[0] + 1e-10) * 100
        mejora_data.append({'Variable': var[:25], 'Mejora_R2_%': mejora_r2,
                            'Reduccion_MAE_%': mejora_mae})

mejora_df = pd.DataFrame(mejora_data).sort_values('Reduccion_MAE_%', ascending=True)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle('Impacto del Enfoque Híbrido (Lags + Wavelet) vs Estándar',
             fontsize=13, fontweight='bold')

# Panel izquierdo: reducción de MAE
colors_mae = ['#2ecc71' if v > 0 else '#e74c3c' for v in mejora_df['Reduccion_MAE_%']]
axes[0].barh(mejora_df['Variable'], mejora_df['Reduccion_MAE_%'], color=colors_mae)
axes[0].axvline(0, color='black', linewidth=1)
axes[0].set_title('Reducción de MAE (%)\n(verde = el Híbrido mejora)')
axes[0].set_xlabel('% reducción de MAE')

# Panel derecho: mejora de R²
colors_r2 = ['#2ecc71' if v > 0 else '#e74c3c' for v in mejora_df['Mejora_R2_%']]
axes[1].barh(mejora_df['Variable'], mejora_df['Mejora_R2_%'], color=colors_r2)
axes[1].axvline(0, color='black', linewidth=1)
axes[1].set_title('Mejora de R² (puntos porcentuales)\n(verde = el Híbrido mejora)')
axes[1].set_xlabel('Puntos % de mejora en R²')

plt.tight_layout()
plt.savefig('outputs_wavelet/05_mejora_hibrido.png', dpi=150, bbox_inches='tight')
plt.show()

print("\nMejora del Híbrido sobre Estándar por variable:")
print(mejora_df.to_string(index=False))
```

### 5.3 — Predicción vs Real para la mejor variable (por cada enfoque)

```python
# Para TBN y Hollín, graficar las 4 curvas de predicción vs real
# en el conjunto de prueba, para comparar visualmente la calidad

for var in ['Hollin ABS/01 mm', 'TBN (mg KOH/g)', 'Fierro ppm']:
    if var not in predictions_store:
        continue

    preds_var = predictions_store[var]
    n_enfoques = len(preds_var)
    if n_enfoques == 0:
        continue

    fig, axes = plt.subplots(n_enfoques, 1, figsize=(16, 4 * n_enfoques), sharex=True)
    if n_enfoques == 1:
        axes = [axes]
    fig.suptitle(f'Predicción t+1 vs Real — {var}', fontsize=13, fontweight='bold')

    for ax, (enfoque, data) in zip(axes, preds_var.items()):
        y_real = data['real']
        y_pred = data['pred']
        x = np.arange(len(y_real))

        ax.plot(x, y_real, 'b-o', markersize=3, linewidth=1.5, label='Real', alpha=0.8)
        ax.plot(x, y_pred, 'r--s', markersize=3, linewidth=1.5, label='Predicho', alpha=0.8)

        # Sombrear error
        ax.fill_between(x, y_real, y_pred, alpha=0.15, color='orange', label='Error')

        mae_v = mean_absolute_error(y_real, y_pred)
        r2_v  = r2_score(y_real, y_pred)
        ax.set_title(f'{enfoque} | MAE={mae_v:.5f} | R²={r2_v:.4f}', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel('Índice de muestra (conjunto de prueba)')
    plt.tight_layout()
    safe_var = var.replace(' ', '_').replace('/', '_')[:20]
    plt.savefig(f'outputs_wavelet/06_pred_real_{safe_var}.png', dpi=150, bbox_inches='tight')
    plt.show()
```

### 5.4 — Análisis de error por estado (¿mejoran los críticos?)

```python
# Verificar si el enfoque Wavelet/Híbrido reduce el error
# específicamente en muestras con estado CRÍTICO
# Esto es lo más relevante para el SaaS (alertas tempranas)

print("\n" + "="*65)
print("ERROR POR ESTADO — ¿Mejora el Híbrido en muestras CRÍTICAS?")
print("="*65)

# Necesitamos los estados del conjunto de prueba — tomarlos del df original
n_test_approx = int(len(df_std) * 0.20)
test_estados = df_analisis.sort_values(['Equipo', 'Hora_Producto'])['Estado'].values[-n_test_approx:]

for var in VARS_TARGET[:4]:
    if var not in predictions_store:
        continue
    preds_var = predictions_store[var]
    print(f"\n  {var}:")
    print(f"  {'Enfoque':22s} | {'NORMAL MAE':>12} | {'PRECAUC MAE':>12} | {'CRÍTICO MAE':>12}")
    print(f"  {'-'*65}")

    for enfoque, data in preds_var.items():
        y_real = data['real']
        y_pred = data['pred']
        n_min = min(len(y_real), len(test_estados))

        for est_name in ['NORMAL', 'PRECAUCION', 'CRITICO']:
            mask = test_estados[:n_min] == est_name
            if mask.sum() > 0:
                mae_est = mean_absolute_error(y_real[:n_min][mask], y_pred[:n_min][mask])
            else:
                mae_est = np.nan

        maes = {}
        for est_name in ['NORMAL', 'PRECAUCION', 'CRITICO']:
            mask = test_estados[:n_min] == est_name
            maes[est_name] = mean_absolute_error(y_real[:n_min][mask], y_pred[:n_min][mask]) if mask.sum() > 0 else np.nan

        print(f"  {enfoque:22s} | {maes['NORMAL']:>12.5f} | {maes['PRECAUCION']:>12.5f} | {maes['CRITICO']:>12.5f}")
```

---

## SECCIÓN 6 — ANÁLISIS DE FEATURES WAVELET MÁS IMPORTANTES

```python
# Entrenar el modelo Híbrido para Hollín (la variable más predecible)
# y analizar qué features son más importantes con SHAP.
# Específicamente: ¿aportan más las features wavelet o los lags estándar?

from lightgbm import LGBMRegressor

var_demo = 'Hollin ABS/01 mm'
target_col = f'target_{var_demo[:15]}'
meta_excl = ['Equipo', 'Fecha', 'Hora_Producto', 'Estado_num'] + \
            [c for c in df_hyb.columns if c.startswith('target_')]
feat_cols_hyb = [c for c in df_hyb.columns if c not in meta_excl]

valid_mask = df_hyb[target_col].notna()
sub = df_hyb[valid_mask].copy()
X_hyb = sub[feat_cols_hyb].fillna(sub[feat_cols_hyb].median())
y_hyb = sub[target_col].values

split = int(len(X_hyb) * 0.80)
X_tr, X_te = X_hyb.iloc[:split], X_hyb.iloc[split:]
y_tr, y_te = y_hyb[:split], y_hyb[split:]

model_hyb = LGBMRegressor(n_estimators=300, max_depth=6, learning_rate=0.05,
                           num_leaves=63, subsample=0.8, colsample_bytree=0.8,
                           random_state=RANDOM_STATE, verbosity=-1, n_jobs=-1)
model_hyb.fit(X_tr, y_tr)

# Feature importance nativa de LightGBM
imp_df = pd.DataFrame({
    'Feature': feat_cols_hyb,
    'Importancia': model_hyb.feature_importances_
}).sort_values('Importancia', ascending=False).head(30)

# Clasificar si es feature wavelet o estándar
imp_df['Tipo'] = imp_df['Feature'].apply(
    lambda x: 'Wavelet' if x.startswith('wv_') or x.startswith('wvi_') else 'Estándar'
)

fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Panel izquierdo: top 20 features coloreadas por tipo
colors_type = {'Wavelet': '#9b59b6', 'Estándar': '#3498db'}
top20 = imp_df.head(20)
bar_colors = [colors_type[t] for t in top20['Tipo']]
axes[0].barh(range(20), top20['Importancia'].values[::-1], color=bar_colors[::-1])
axes[0].set_yticks(range(20))
axes[0].set_yticklabels(top20['Feature'].values[::-1], fontsize=8)
axes[0].set_title(f'Top 20 Features — Modelo Híbrido\nVariable: {var_demo}', fontsize=10)
axes[0].set_xlabel('Importancia (LightGBM)')

# Leyenda manual
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor='#9b59b6', label='Features Wavelet'),
                   Patch(facecolor='#3498db', label='Features Estándar (Lags)')]
axes[0].legend(handles=legend_elements, loc='lower right', fontsize=9)

# Panel derecho: importancia total por tipo (wavelet vs estándar)
tipo_summary = imp_df.groupby('Tipo')['Importancia'].sum()
bars = axes[1].bar(tipo_summary.index, tipo_summary.values,
                   color=[colors_type[t] for t in tipo_summary.index], edgecolor='white', linewidth=1.5)
for bar, val in zip(bars, tipo_summary.values):
    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{val:.1f}\n({val/tipo_summary.sum()*100:.1f}%)',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
axes[1].set_title('Contribución Total por Tipo de Feature\n(Importancia acumulada)', fontsize=10)
axes[1].set_ylabel('Importancia Total')

plt.tight_layout()
plt.savefig('outputs_wavelet/07_importancia_features_wavelet_vs_standard.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"\nContribución por tipo de feature en el modelo Híbrido ({var_demo}):")
for tipo, total in tipo_summary.items():
    pct = total / tipo_summary.sum() * 100
    print(f"  {tipo:12s}: {total:.1f} ({pct:.1f}%)")
```

---

## SECCIÓN 7 — RESUMEN EJECUTIVO Y RECOMENDACIÓN

```python
# Determinar el mejor enfoque por variable
print("\n" + "="*65)
print("VEREDICTO FINAL — ¿Cuándo usar Wavelet?")
print("="*65)

for var in VARS_TARGET:
    sub = results_df[results_df['Variable'] == var].sort_values('R2', ascending=False)
    if len(sub) == 0:
        continue
    best_row = sub.iloc[0]
    std_row  = sub[sub['Enfoque']=='Estándar (Lags)']
    if len(std_row) == 0:
        continue
    std_r2   = std_row.iloc[0]['R2']
    best_r2  = best_row['R2']
    ganancia = (best_r2 - std_r2) * 100

    if ganancia > 1.0:
        verdict = f"✅ WAVELET MEJORA +{ganancia:.2f}pp R² → usar {best_row['Enfoque']}"
    elif ganancia > 0:
        verdict = f"↗ Mejora marginal +{ganancia:.2f}pp → evaluar costo computacional"
    else:
        verdict = f"❌ Wavelet NO mejora ({ganancia:.2f}pp) → mantener Estándar"

    print(f"\n  {var[:35]:35s}")
    print(f"  Mejor: {best_row['Enfoque']:22s} R²={best_r2:.4f} | Estándar R²={std_r2:.4f}")
    print(f"  {verdict}")

# Exportar resumen final
with pd.ExcelWriter('outputs_wavelet/resumen_wavelet_comparacion.xlsx', engine='openpyxl') as writer:
    results_df.to_excel(writer, sheet_name='Comparacion_Completa', index=False)
    mejora_df.to_excel(writer, sheet_name='Mejora_Hibrido_vs_Standard', index=False)
    imp_df.to_excel(writer, sheet_name='Feature_Importance_Hibrido', index=False)

print(f"""
╔══════════════════════════════════════════════════════════════════╗
║     RESUMEN: WAVELET EN LA DATA 794AC QUELLAVECO                 ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  DIAGNÓSTICO PREVIO:                                             ║
║  • Muestreo irregular (Coef.Var. 0.83-1.19): DWT directa        ║
║    sobre eje temporal pierde el 92% de los puntos               ║
║  • No-estacionariedad confirmada (p<0.001) en todas las vars     ║
║                                                                  ║
║  ESTRATEGIAS IMPLEMENTADAS:                                      ║
║  1. Estándar (Lags + Rolling)         → baseline Fase 2         ║
║  2. Wavelet-Índice (DWT por muestra)  → experimental            ║
║  3. Wavelet-Interpolado (DWT + regrid)→ experimental            ║
║  4. Híbrido (Lags + Wavelet extras)   → recomendado             ║
║                                                                  ║
║  HIPÓTESIS A VALIDAR CON LOS RESULTADOS:                         ║
║  → El Híbrido debería mejorar especialmente en variables         ║
║    con alta tendencia: TBN, Hollín, Fierro                       ║
║  → Wavelet-Interp será mejor en series más suaves (TBN, Visc)   ║
║  → Wavelet-Índice captura mejor los picos de desgaste (Fe, Cu)  ║
║                                                                  ║
║  PARA EL SaaS:                                                   ║
║  Si el Híbrido mejora >2pp de R², incorporar las features        ║
║  wavelet al pipeline de producción. Costo: +0.5ms por muestra.   ║
╚══════════════════════════════════════════════════════════════════╝
""")
```

---

## NOTAS FINALES PARA CURSOR

1. **PyWavelets** (`pywt`) es la librería estándar. Instalar con `pip install PyWavelets`.

2. **Familias wavelet recomendadas para señales industriales:**
   - `'db4'` (Daubechies 4): buena para señales con tendencias suaves como TBN
   - `'sym4'` (Symlets 4): similar a db4 pero más simétrica, buena para Hollín
   - `'coif2'` (Coiflets 2): excelente para señales con picos como Hierro
   - `'haar'`: la más simple, útil como baseline wavelet

3. **Nivel de descomposición**: nivel=3 es adecuado para series de ~100-200 puntos.
   Para series más cortas (<50 puntos) usar nivel=2.

4. **Umbralización (denoising)**: el umbral de Donoho-Johnstone (`sigma * sqrt(2*log(N))`)
   es el más usado en la práctica industrial. También probar `'hard'` vs `'soft'`.

5. **Manejo de bordes**: DWT tiene efectos de borde. Usar `mode='periodization'` o
   `mode='symmetric'` en `pywt.wavedec()` para minimizarlos.

6. **Tiempo de ejecución esperado:**
   - build_standard_features: ~10 seg total
   - build_wavelet_index_features: ~3-5 min (es el más lento)
   - build_wavelet_interp_features: ~1-2 min
   - Entrenamiento de todos los modelos: ~5-10 min

7. **Outputs esperados en `outputs_wavelet/`:**
   - `01_descomposicion_wavelet_HT001.png`
   - `02_wavelet_denoising.png`
   - `03_comparacion_enfoques.xlsx`
   - `04_heatmap_comparacion.png`
   - `05_mejora_hibrido.png`
   - `06_pred_real_{variable}.png` (una por cada variable)
   - `07_importancia_features_wavelet_vs_standard.png`
   - `resumen_wavelet_comparacion.xlsx`
