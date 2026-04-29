# PROMPT PARA CURSOR — Notebook de Exploración Avanzada: Ciclo de Vida y Predicción t+1
## Flota 794AC — Mina Quellaveco

---

## CONTEXTO DEL PROYECTO

Estás trabajando con la base de datos de **muestras de aceite de motor** de la flota de
camiones de extracción minera **Caterpillar 794AC** de la mina **Quellaveco (Perú)**.
El archivo principal es un Excel con múltiples hojas; la hoja clave se llama `'794AC QUELLA'`.

El objetivo final es construir un **SaaS predictivo de mantenimiento** que, a partir del
historial de muestras de aceite de cada camión, sea capaz de:
1. Predecir los valores de la **próxima muestra (t+1)**
2. Predecir el **estado futuro** del camión (NORMAL / PRECAUCION / CRITICO)
3. Estimar **cuántas horas de operación** quedan antes de entrar en estado CRÍTICO

Este notebook cubre la **Fase 1: Exploración Profunda del Ciclo de Vida** que
alimentará el modelado predictivo posterior.

---

## ESTRUCTURA DE LA BASE DE DATOS

**Archivo:** `DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx`
**Hoja principal:** `794AC QUELLA`
**Dimensiones:** 3,719 filas × 58 columnas

### Columnas principales:
```
Identificadores:
  - Codigo          → ID único de la muestra (str)
  - Fecha           → Fecha de la muestra (datetime)
  - Fecha - Año     → Periodo mes-año (str)
  - Equipo          → ID del camión: HT001 a HT030 + HT051-053 (str)
  - Producto        → Lubricante usado (str)
  - Hora_Producto   → Horas de servicio del aceite en el momento de la muestra (int)

Variable objetivo:
  - Estado          → NORMAL | PRECAUCION | CRITICO (str)
  - Distribución conocida: NORMAL=12.8%, PRECAUCION=56.4%, CRITICO=30.8%

Propiedades del lubricante (salud del aceite):
  - TBN (mg KOH/g)           → Reserva alcalina (degrada con el tiempo, rango ideal: >7.5)
  - Viscosidad a 100 °C cSt  → Viscosidad cinemática (rango ideal: 12.5-15.5 cSt)
  - Viscosidad a 40 °C cSt   → (69% nulos — usar con cuidado)
  - Oxidación ABS/01 mm      → Oxidación del aceite (límite crítico: ~0.15)
  - Nitración ABS/01 mm      → Nitración (límite crítico: ~0.10)
  - Sulfatación ABS/01 mm    → Sulfatación (límite crítico: ~0.05)
  - Hollin ABS/01 mm         → Hollín (carbonilla) - predictor #1, límite: ~1.0)
  - Indice de Viscosidad     → (73% nulos — excluir del análisis principal)

Contaminantes:
  - Glycol %       → Contaminación por refrigerante (límite: >0)
  - Diesel %       → Dilución por combustible
  - Agua %         → Contaminación por agua
  - Potasio ppm    → Indicador de fuga de refrigerante (límite crítico: >5)
  - Silicio ppm    → Contaminación por tierra/arena (límite: >25)
  - Sodio ppm      → Contaminación por agua o refrigerante

Metales de desgaste (ppm):
  - Fierro ppm     → Desgaste de componentes ferrosos (límite: >50 ppm)
  - Cromo ppm      → Desgaste de anillos/camisas (límite: >5 ppm)
  - Plomo ppm      → Desgaste de cojinetes (límite: >10 ppm)
  - Cobre ppm      → Desgaste de cojinetes/bujes (límite: >20 ppm)
  - Aluminio ppm   → Desgaste de pistones (límite: >15 ppm)
  - Estaño ppm     → Desgaste de cojinetes
  - Niquel ppm     → Desgaste de válvulas
  - Manganeso ppm
  - Plata ppm

Metales acumulados (desde el último cambio de aceite):
  - Fe Acum ppm, Cr Acum ppm, Pb Acum ppm, Cu Acum ppm, Sn Acum ppm,
    Al Acum ppm, Si Acum ppm
  → NOTA: estas columnas tienen ~36% de nulos

Indicadores adicionales:
  - TD Fe, TD Pb, TD Cu   → Tasa de desgaste (ratio acumulado/horas)
  - Particulas Ferrosas (PQ)  → Partículas ferrosas magnéticas
  - Agua ppm               → (99.7% nulos — excluir)

Texto libre:
  - Observacion       → Comentario del analista
  - Accion_Sugerida   → Acción recomendada (98% nulos)
```

### Datos de muestreo ya conocidos:
- Equipos activos: 30 camiones (HT001-HT030) + 3 recientes (HT051-053)
- Muestreo promedio: cada **7.7 días** (mediana: 5 días) — MUY IRREGULAR
- Horas entre muestras: promedio **80-120 horas** de operación
- Rango de fechas: **Feb 2020 — Mar 2024**
- Equipos con >100 muestras: **25 de 30** (suficiente para modelado)
- Autocorrelaciones lag-1 conocidas (HT001): TBN=0.76, Visc=0.67, Oxidación=0.60,
  Cobre=0.50, Potasio=0.51, Hollín=0.47, Hierro=0.36

---

## INSTRUCCIONES PARA EL NOTEBOOK

Crea un **Jupyter Notebook Python** completo, bien documentado, con celdas Markdown
explicativas entre secciones. El notebook debe llamarse:
`exploracion_ciclo_vida_794AC.ipynb`

Usa las siguientes librerías (todas disponibles en entorno estándar):
```python
pandas, numpy, matplotlib, seaborn, scipy, sklearn, statsmodels, warnings
```

---

## SECCIÓN 1 — CONFIGURACIÓN E IMPORTACIONES

```python
# Celda 1: imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy import stats
from scipy.signal import savgol_filter
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import warnings
warnings.filterwarnings('ignore')

# Configuración visual
plt.rcParams['figure.dpi'] = 120
plt.rcParams['font.size'] = 10
sns.set_style('whitegrid')
sns.set_palette('husl')

# Ruta del archivo — AJUSTAR según ubicación local
FILE_PATH = 'DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx'
SHEET_NAME = '794AC QUELLA'

# Variables clave de análisis
VARS_SALUD = ['TBN (mg KOH/g)', 'Viscosidad a 100 °C cSt', 'Oxidación ABS/01 mm',
              'Nitración ABS/01 mm', 'Sulfatación ABS/01 mm', 'Hollin ABS/01 mm']

VARS_DESGASTE = ['Fierro ppm', 'Cromo ppm', 'Plomo ppm', 'Cobre ppm',
                 'Aluminio ppm', 'Estaño ppm']

VARS_CONTAMINANTES = ['Silicio ppm', 'Potasio ppm', 'Sodio ppm']

VARS_TARGET = VARS_SALUD + VARS_DESGASTE + VARS_CONTAMINANTES

# Límites de alerta por variable (para líneas de referencia en gráficos)
LIMITES = {
    'TBN (mg KOH/g)': {'precaucion': 8.0, 'critico': 7.5, 'direction': 'lower'},
    'Viscosidad a 100 °C cSt': {'precaucion': 13.0, 'critico': 12.5, 'direction': 'lower'},
    'Oxidación ABS/01 mm': {'precaucion': 0.10, 'critico': 0.15, 'direction': 'upper'},
    'Hollin ABS/01 mm': {'precaucion': 0.70, 'critico': 1.00, 'direction': 'upper'},
    'Fierro ppm': {'precaucion': 30, 'critico': 50, 'direction': 'upper'},
    'Cobre ppm': {'precaucion': 10, 'critico': 20, 'direction': 'upper'},
    'Silicio ppm': {'precaucion': 15, 'critico': 25, 'direction': 'upper'},
    'Potasio ppm': {'precaucion': 3, 'critico': 5, 'direction': 'upper'},
}
```

---

## SECCIÓN 2 — CARGA Y LIMPIEZA DE DATOS

```python
# Celda 2: Carga del dataset
df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
df['Fecha'] = pd.to_datetime(df['Fecha'])
df['Hora_Producto'] = pd.to_numeric(df['Hora_Producto'], errors='coerce')

# Convertir variables numéricas
for col in VARS_TARGET:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Ordenar por equipo y fecha
df = df.sort_values(['Equipo', 'Fecha', 'Hora_Producto']).reset_index(drop=True)

# Codificar Estado como ordinal para análisis numérico
estado_map = {'NORMAL': 0, 'PRECAUCION': 1, 'CRITICO': 2}
df['Estado_num'] = df['Estado'].map(estado_map)

print(f"Dataset cargado: {df.shape[0]} filas × {df.shape[1]} columnas")
print(f"Equipos: {sorted(df['Equipo'].unique())}")
print(f"Período: {df['Fecha'].min().date()} → {df['Fecha'].max().date()}")
print(f"\nDistribución de estados:")
print(df['Estado'].value_counts(normalize=True).mul(100).round(1).to_string())
```

---

## SECCIÓN 3 — ANÁLISIS DE FRECUENCIA DE MUESTREO

### 3.1 — Estadísticas de muestreo por equipo
```python
# Para cada equipo, calcular:
# - Número total de muestras
# - Fecha inicio y fin
# - Días de operación monitoreada
# - Intervalo promedio, mediana, min, max entre muestras (en días)
# - Intervalo promedio en horas de producto
# - Número de gaps > 30 días
# - Número de muestras el mismo día (duplicados de fecha)

sampling_stats = []
for equipo, grp in df.groupby('Equipo'):
    grp = grp.sort_values('Fecha')
    n = len(grp)
    diffs_dias = grp['Fecha'].diff().dt.days.dropna()
    diffs_horas = grp['Hora_Producto'].diff().dropna()
    diffs_horas_pos = diffs_horas[diffs_horas > 0]  # Solo positivos

    sampling_stats.append({
        'Equipo': equipo,
        'N_muestras': n,
        'Fecha_inicio': grp['Fecha'].min().date(),
        'Fecha_fin': grp['Fecha'].max().date(),
        'Span_dias': (grp['Fecha'].max() - grp['Fecha'].min()).days,
        'Intervalo_dias_prom': round(diffs_dias.mean(), 1),
        'Intervalo_dias_mediana': round(diffs_dias.median(), 1),
        'Intervalo_dias_max': int(diffs_dias.max()) if len(diffs_dias) > 0 else 0,
        'Gaps_mayores_30d': int((diffs_dias > 30).sum()),
        'Duplicados_fecha': int((diffs_dias == 0).sum()),
        'Intervalo_horas_prom': round(diffs_horas_pos.mean(), 1) if len(diffs_horas_pos) > 0 else np.nan,
        'Intervalo_horas_mediana': round(diffs_horas_pos.median(), 1) if len(diffs_horas_pos) > 0 else np.nan,
        'Hora_max_registrada': grp['Hora_Producto'].max(),
        'Pct_critico': round((grp['Estado']=='CRITICO').sum()/n*100, 1),
        'Pct_normal': round((grp['Estado']=='NORMAL').sum()/n*100, 1),
    })

sampling_df = pd.DataFrame(sampling_stats).sort_values('N_muestras', ascending=False)
print(sampling_df.to_string(index=False))
```

### 3.2 — Heatmap del calendario de muestreo
```python
# Crear una matriz Equipo × Mes-Año que muestre el número de muestras
# tomadas cada mes por cada equipo.
# Visualizar como heatmap (equipos en filas, meses en columnas)
# Esto permite ver: ¿hay períodos sin muestreo? ¿Algún camión fue retirado?

df['YearMonth'] = df['Fecha'].dt.to_period('M')
pivot_calendar = pd.crosstab(df['Equipo'], df['YearMonth'])

fig, ax = plt.subplots(figsize=(24, 10))
sns.heatmap(pivot_calendar, cmap='YlOrRd', linewidths=0.3,
            cbar_kws={'label': 'N° muestras/mes'},
            ax=ax, annot=False)
ax.set_title('Calendario de Muestreo por Equipo\n(N° de muestras por mes)',
             fontsize=14, fontweight='bold')
ax.set_xlabel('Período (Mes-Año)')
ax.set_ylabel('Equipo')
plt.xticks(rotation=45, ha='right', fontsize=7)
plt.tight_layout()
plt.savefig('outputs/01_calendario_muestreo.png', dpi=150, bbox_inches='tight')
plt.show()
```

### 3.3 — Distribución de intervalos entre muestras
```python
# Para toda la flota, graficar histograma de días entre muestras
# Identificar si la distribución es bimodal (hay dos patrones de muestreo)
# Separar análisis por equipo con más muestras (top 6)
```

---

## SECCIÓN 4 — CURVAS DE DEGRADACIÓN POR HORAS DE PRODUCTO

> CONCEPTO CLAVE: No usar la fecha como eje X, sino las **Horas_Producto** (horas de
> servicio del aceite). Cada cambio de aceite resetea el contador a 0. Las horas son
> el índice real de "edad" del lubricante.

### 4.1 — Curvas de degradación individuales por equipo (todas las variables)
```python
# Para cada uno de los 6 equipos con más muestras (HT001, HT005, HT012, HT011, HT006, HT002):
# Crear una figura de 3×3 subplots (o 3 filas × 3 cols) con las variables en VARS_SALUD y VARS_DESGASTE
# En cada subplot:
#   - Scatter de puntos coloreados por Estado (verde=NORMAL, naranja=PRECAUCION, rojo=CRITICO)
#   - Línea suavizada (rolling mean de ventana 5) sobre el scatter
#   - Líneas horizontales de referencia: precaución (naranja) y crítico (rojo) si aplica
#   - Eje X: Hora_Producto (0 a max)
#   - Eje Y: valor de la variable
# El título del subplot debe mostrar la variable y la autocorrelación lag-1 del equipo
# Guardar cada figura en 'outputs/curva_degradacion_{EQUIPO}.png'

COLORES_ESTADO = {'NORMAL': '#2ecc71', 'PRECAUCION': '#f39c12', 'CRITICO': '#e74c3c'}

equipos_top = df.groupby('Equipo').size().sort_values(ascending=False).head(6).index.tolist()

for equipo in equipos_top:
    grp = df[df['Equipo']==equipo].sort_values('Hora_Producto').copy()
    vars_plot = [v for v in VARS_TARGET if v in df.columns and grp[v].notna().sum() > 10][:9]

    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    axes = axes.flatten()
    fig.suptitle(f'Curvas de Degradación — {equipo} ({len(grp)} muestras)',
                 fontsize=14, fontweight='bold', y=1.01)

    for i, var in enumerate(vars_plot):
        ax = axes[i]
        s = grp[['Hora_Producto', var, 'Estado']].dropna(subset=[var])

        # Scatter coloreado por estado
        for estado, color in COLORES_ESTADO.items():
            mask = s['Estado'] == estado
            ax.scatter(s.loc[mask, 'Hora_Producto'], s.loc[mask, var],
                      c=color, alpha=0.6, s=30, label=estado)

        # Línea suavizada (rolling mean)
        s_sorted = s.sort_values('Hora_Producto')
        if len(s_sorted) >= 5:
            rolling = s_sorted[var].rolling(window=5, center=True, min_periods=2).mean()
            ax.plot(s_sorted['Hora_Producto'], rolling, 'b-', linewidth=1.5, alpha=0.8)

        # Líneas de referencia si existen
        if var in LIMITES:
            lim = LIMITES[var]
            ax.axhline(lim['precaucion'], color='orange', linestyle='--', alpha=0.7, linewidth=1)
            ax.axhline(lim['critico'], color='red', linestyle='--', alpha=0.7, linewidth=1)

        # Calcular autocorrelación
        ac1 = s[var].autocorr(lag=1) if len(s) > 3 else np.nan

        ax.set_title(f'{var[:35]}\nAutocorr lag-1: {ac1:.3f}', fontsize=8)
        ax.set_xlabel('Horas de Producto', fontsize=8)
        ax.set_ylabel(var[:20], fontsize=7)
        if i == 0:
            ax.legend(fontsize=6, loc='upper left')

    # Desactivar ejes sobrantes
    for j in range(len(vars_plot), len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plt.savefig(f'outputs/curva_degradacion_{equipo}.png', dpi=150, bbox_inches='tight')
    plt.show()
    print(f"✓ {equipo} graficado")
```

### 4.2 — Curva de degradación promedio de la FLOTA (benchmark)
```python
# Crear una curva de degradación promedio de toda la flota
# dividiendo las horas de producto en bins de 50 horas (0-50, 50-100, ..., 900-950)
# Para cada bin: calcular media, P25, P75 de cada variable clave
# Graficar con banda de confianza (P25-P75 sombreado, media como línea)
# Esta curva es el "perfil de vida típico del aceite" en estos motores
# Incluir también la proporción de estados por bin como gráfico de barras apiladas

bin_size = 50
max_horas = 1000
bins = range(0, max_horas + bin_size, bin_size)
df['Hora_bin'] = pd.cut(df['Hora_Producto'], bins=list(bins), right=False,
                         labels=[f"{b}-{b+bin_size}" for b in list(bins)[:-1]])

# Variables a graficar en la curva flota
vars_flota = ['TBN (mg KOH/g)', 'Viscosidad a 100 °C cSt', 'Hollin ABS/01 mm',
              'Fierro ppm', 'Oxidación ABS/01 mm', 'Cobre ppm']

fig, axes = plt.subplots(3, 2, figsize=(16, 14))
axes = axes.flatten()
fig.suptitle('Curva de Degradación Promedio de la Flota 794AC\n(Toda la flota, por horas de producto)',
             fontsize=13, fontweight='bold')

for i, var in enumerate(vars_flota):
    ax = axes[i]
    grouped = df.groupby('Hora_bin', observed=True)[var].agg(['mean','median',
              lambda x: x.quantile(0.25), lambda x: x.quantile(0.75),
              'count']).reset_index()
    grouped.columns = ['Hora_bin', 'mean', 'median', 'p25', 'p75', 'n']
    grouped = grouped[grouped['n'] >= 5]  # Mínimo 5 muestras por bin

    x = range(len(grouped))
    ax.fill_between(x, grouped['p25'], grouped['p75'], alpha=0.3, color='steelblue', label='P25-P75')
    ax.plot(x, grouped['mean'], 'b-o', markersize=3, linewidth=2, label='Media')
    ax.plot(x, grouped['median'], 'g--', linewidth=1.5, alpha=0.7, label='Mediana')

    if var in LIMITES:
        lim = LIMITES[var]
        ax.axhline(lim['precaucion'], color='orange', linestyle=':', linewidth=1.5,
                   label=f"Lím. Precaución")
        ax.axhline(lim['critico'], color='red', linestyle=':', linewidth=1.5,
                   label=f"Lím. Crítico")

    ax.set_xticks(x[::2])
    ax.set_xticklabels([grouped['Hora_bin'].iloc[j] for j in x[::2]], rotation=45, ha='right', fontsize=7)
    ax.set_title(f'{var}', fontsize=10)
    ax.set_xlabel('Horas de Producto (bins de 50h)')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('outputs/02_curva_degradacion_flota.png', dpi=150, bbox_inches='tight')
plt.show()
```

### 4.3 — Distribución de estados por bin de horas
```python
# Crear un gráfico de barras apiladas (100%) mostrando qué % de muestras
# son NORMAL / PRECAUCION / CRITICO en cada bin de horas (0-50, 50-100, etc.)
# Esto responde: "¿A partir de qué hora empieza a aumentar el riesgo crítico?"
# Este es uno de los hallazgos más importantes para el SaaS

estado_por_hora = pd.crosstab(df['Hora_bin'], df['Estado'], normalize='index') * 100
estado_por_hora = estado_por_hora.reindex(columns=['NORMAL', 'PRECAUCION', 'CRITICO'], fill_value=0)

fig, ax = plt.subplots(figsize=(16, 6))
estado_por_hora.plot(kind='bar', stacked=True, ax=ax,
                     color=['#2ecc71', '#f39c12', '#e74c3c'],
                     edgecolor='white', linewidth=0.5)

ax.set_title('Distribución de Estados por Rango de Horas de Producto\n(¿Cuándo aumenta el riesgo?)',
             fontsize=13, fontweight='bold')
ax.set_xlabel('Horas de Producto')
ax.set_ylabel('% de muestras')
ax.set_ylim(0, 100)
ax.legend(loc='upper right')
ax.tick_params(axis='x', rotation=45)

# Agregar línea que marca el punto de inflexión
plt.tight_layout()
plt.savefig('outputs/03_estados_por_hora.png', dpi=150, bbox_inches='tight')
plt.show()

# Imprimir tabla numérica
print("\nPorcentaje de estados CRITICOS por bin de horas:")
print(estado_por_hora[['CRITICO']].round(1).to_string())
```

---

## SECCIÓN 5 — ANÁLISIS ESTADÍSTICO DE SERIES TEMPORALES POR EQUIPO

### 5.1 — Autocorrelación y PACF de variables clave
```python
# Para los top 6 equipos, calcular ACF y PACF de las variables:
# TBN, Viscosidad 100°C, Hollín, Fierro, Oxidación
# Ordenar por Hora_Producto (no por fecha)
# Graficar las funciones ACF y PACF (hasta lag 20)
# También realizar el test de Dickey-Fuller aumentado (ADF) para verificar
# si la serie es estacionaria (importante para decidir el tipo de modelo t+1)
# Guardar los p-values del ADF en una tabla resumen

adf_results = []

for equipo in equipos_top:
    grp = df[df['Equipo']==equipo].sort_values('Hora_Producto').copy()

    fig, axes = plt.subplots(len(VARS_SALUD[:4]), 2, figsize=(14, 16))
    fig.suptitle(f'ACF y PACF — {equipo}', fontsize=13, fontweight='bold')

    for i, var in enumerate(VARS_SALUD[:4]):
        s = grp[var].dropna().values
        if len(s) < 20:
            continue

        # ACF
        plot_acf(s, lags=20, ax=axes[i][0], title=f'{var[:30]} — ACF', alpha=0.05)
        # PACF
        plot_pacf(s, lags=20, ax=axes[i][1], title=f'{var[:30]} — PACF', alpha=0.05)

        # ADF test
        try:
            adf_result = adfuller(s, autolag='AIC')
            is_stationary = adf_result[1] < 0.05
            adf_results.append({
                'Equipo': equipo, 'Variable': var,
                'ADF_stat': round(adf_result[0], 4),
                'p_value': round(adf_result[1], 4),
                'Estacionaria': 'Sí' if is_stationary else 'No',
                'N': len(s)
            })
        except:
            pass

    plt.tight_layout()
    plt.savefig(f'outputs/acf_pacf_{equipo}.png', dpi=120, bbox_inches='tight')
    plt.show()

adf_df = pd.DataFrame(adf_results)
print("\nResumen ADF - Estacionariedad de las series:")
print(adf_df.to_string(index=False))
```

### 5.2 — Heatmap de autocorrelaciones (lag 1 y lag 2) por equipo y variable
```python
# Calcular autocorrelación lag-1 y lag-2 para TODAS las variables clave
# en TODOS los equipos con >50 muestras
# Visualizar como heatmap (Variables × Equipos)
# Esto muestra qué variables son más predecibles en qué equipos

ac_matrix = {}
equipos_suficientes = df.groupby('Equipo').size()[df.groupby('Equipo').size() >= 50].index.tolist()

for equipo in equipos_suficientes:
    grp = df[df['Equipo']==equipo].sort_values('Hora_Producto')
    ac_matrix[equipo] = {}
    for var in VARS_TARGET:
        if var in grp.columns:
            s = pd.to_numeric(grp[var], errors='coerce').dropna()
            if len(s) >= 20:
                ac_matrix[equipo][var] = round(s.autocorr(lag=1), 3)
            else:
                ac_matrix[equipo][var] = np.nan

ac_df = pd.DataFrame(ac_matrix).T  # equipos en filas, variables en columnas
ac_df = ac_df.dropna(how='all', axis=1)

fig, ax = plt.subplots(figsize=(20, 10))
sns.heatmap(ac_df.T, cmap='RdYlGn', center=0, vmin=-1, vmax=1,
            annot=True, fmt='.2f', linewidths=0.3,
            cbar_kws={'label': 'Autocorrelación lag-1'}, ax=ax, annot_kws={'size': 7})
ax.set_title('Autocorrelación Lag-1 por Variable y Equipo\n(Verde = alta predecibilidad, Rojo = baja)',
             fontsize=13, fontweight='bold')
ax.set_xlabel('Equipo')
ax.set_ylabel('Variable')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('outputs/04_heatmap_autocorrelacion.png', dpi=150, bbox_inches='tight')
plt.show()

print("\nVariables más predecibles (autocorr lag-1 promedio por variable):")
print(ac_df.mean().sort_values(ascending=False).round(3).to_string())
```

---

## SECCIÓN 6 — INGENIERÍA DE FEATURES PARA PREDICCIÓN t+1

> Esta sección construye el dataset de features de lag que se usará para el modelo predictivo.
> Para cada muestra t, construir features de las t-1, t-2, t-3 muestras anteriores.

### 6.1 — Construcción del dataset con lags
```python
# Para cada equipo, ordenar por Hora_Producto y crear:
# - lag_1_{variable}: valor de la muestra t-1
# - lag_2_{variable}: valor de la muestra t-2
# - lag_3_{variable}: valor de la muestra t-3
# - delta_1_{variable}: diferencia entre t y t-1 (tasa de cambio)
# - horas_desde_ultima: diferencia en Hora_Producto entre t y t-1
# - estado_lag1: estado de la muestra anterior (codificado numéricamente)
# Hacer esto solo para las variables en VARS_SALUD + VARS_DESGASTE

VARS_LAG = ['TBN (mg KOH/g)', 'Viscosidad a 100 °C cSt', 'Hollin ABS/01 mm',
            'Fierro ppm', 'Oxidación ABS/01 mm', 'Cobre ppm', 'Potasio ppm']
N_LAGS = 3  # Número de muestras pasadas a incluir como features

dfs_lag = []
for equipo, grp in df.groupby('Equipo'):
    grp = grp.sort_values('Hora_Producto').copy()
    grp_lag = grp.copy()

    for var in VARS_LAG:
        if var in grp.columns:
            for lag in range(1, N_LAGS + 1):
                grp_lag[f'lag{lag}_{var[:20]}'] = grp[var].shift(lag)
                if lag == 1:
                    grp_lag[f'delta_{var[:20]}'] = grp[var].diff()

    grp_lag['horas_desde_ultima'] = grp['Hora_Producto'].diff()
    grp_lag['estado_lag1'] = grp['Estado_num'].shift(1)
    grp_lag['estado_lag2'] = grp['Estado_num'].shift(2)

    # Rolling stats (ventana de 3)
    for var in VARS_LAG[:4]:
        if var in grp.columns:
            grp_lag[f'roll3_mean_{var[:15]}'] = grp[var].rolling(3, min_periods=2).mean()
            grp_lag[f'roll3_std_{var[:15]}'] = grp[var].rolling(3, min_periods=2).std()

    dfs_lag.append(grp_lag)

df_lag = pd.concat(dfs_lag, ignore_index=True)

# Eliminar filas donde no hay al menos 2 lags disponibles
df_lag = df_lag.dropna(subset=[f'lag2_{VARS_LAG[0][:20]}'])
print(f"Dataset con lags construido: {df_lag.shape[0]} muestras × {df_lag.shape[1]} columnas")
print(f"Features de lag generadas: {[c for c in df_lag.columns if 'lag' in c or 'delta' in c or 'roll' in c][:15]}...")
```

### 6.2 — Análisis de correlación: features de lag vs variable target
```python
# Para cada variable target en VARS_LAG, calcular la correlación de:
# - lag1, lag2, lag3 con el valor actual (t)
# - delta_1 con el valor actual
# - horas_desde_ultima con el valor actual
# Mostrar en una tabla ordenada por correlación absoluta
# Esto indica cuáles features de lag son más predictivas para cada variable

print("="*70)
print("CORRELACIÓN DE FEATURES DE LAG CON VARIABLE TARGET")
print("="*70)

for var in VARS_LAG[:5]:
    var_short = var[:20]
    target = var
    feature_cols = ([f'lag{i}_{var_short}' for i in range(1, N_LAGS+1)] +
                    [f'delta_{var_short}', 'horas_desde_ultima', 'estado_lag1',
                     f'roll3_mean_{var[:15]}'])

    feature_cols_exist = [c for c in feature_cols if c in df_lag.columns]

    corrs = {}
    for feat in feature_cols_exist:
        mask = df_lag[feat].notna() & df_lag[target].notna()
        if mask.sum() > 30:
            r, p = stats.pearsonr(df_lag.loc[mask, feat], df_lag.loc[mask, target])
            corrs[feat] = (round(r, 4), round(p, 4))

    print(f"\n  TARGET: {var}")
    print(f"  {'Feature':<35} {'Correlación':>12} {'p-value':>12}")
    for feat, (r, p) in sorted(corrs.items(), key=lambda x: abs(x[1][0]), reverse=True):
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        print(f"  {feat:<35} {r:>+12.4f} {p:>10.4f} {sig}")
```

### 6.3 — Modelo baseline de predicción t+1 por regresión
```python
# Para cada variable en VARS_LAG, entrenar un modelo de regresión simple usando
# las features de lag como predictores y la variable actual como target
# Usar: Linear Regression (baseline) y Random Forest Regressor (modelo mejorado)
# Split: 80% train / 20% test, ordenado temporalmente (no shuffle)
# Métricas: MAE, RMSE, R2
# Presentar resultados en tabla comparativa

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split

print("="*70)
print("MODELO BASELINE t+1 — PREDICCIÓN DE PRÓXIMA MUESTRA")
print("="*70)

results = []
for var in VARS_LAG:
    var_short = var[:20]

    feature_cols = ([f'lag{i}_{var_short}' for i in range(1, N_LAGS+1)] +
                    [f'delta_{var_short}', 'horas_desde_ultima', 'estado_lag1',
                     f'roll3_mean_{var[:15]}', 'Hora_Producto'])
    feature_cols_exist = [c for c in feature_cols if c in df_lag.columns]

    subset = df_lag[[var] + feature_cols_exist].dropna()
    if len(subset) < 100:
        continue

    X = subset[feature_cols_exist].values
    y = subset[var].values

    # Split temporal
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # Modelo 1: Ridge Regression (baseline)
    ridge = Ridge()
    ridge.fit(X_train, y_train)
    y_pred_r = ridge.predict(X_test)

    # Modelo 2: Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)

    for name, y_pred in [('Ridge', y_pred_r), ('RandomForest', y_pred_rf)]:
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        results.append({'Variable': var, 'Modelo': name, 'MAE': round(mae, 4),
                        'RMSE': round(rmse, 4), 'R2': round(r2, 4), 'N_test': len(y_test)})

results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))

# Guardar resultados
results_df.to_excel('outputs/baseline_prediccion_t1.xlsx', index=False)
print("\n✓ Resultados guardados en 'outputs/baseline_prediccion_t1.xlsx'")
```

### 6.4 — Visualización de predicción vs real (por equipo)
```python
# Para el mejor modelo (Random Forest) y la variable más predictible (TBN o Viscosidad):
# Graficar la predicción t+1 vs el valor real en el conjunto de prueba
# Hacer esto específicamente para HT001 y HT012 (más muestras)
# Graficar también el error absoluto en el tiempo para ver si hay patrones
# en dónde falla el modelo (¿falla más en cambios de aceite? ¿en estados críticos?)
```

---

## SECCIÓN 7 — ANÁLISIS DE PUNTO DE QUIEBRE (DEGRADACIÓN CRÍTICA)

### 7.1 — ¿A cuántas horas se vuelve crítico cada equipo?
```python
# Para cada equipo, encontrar las secuencias de muestras donde:
# Estado pasa de PRECAUCION a CRITICO
# Registrar las Horas_Producto en ese punto de transición
# Calcular estadísticas: horas promedio, mediana, min, max para entrar en CRITICO

transiciones = []
for equipo, grp in df.groupby('Equipo'):
    grp = grp.sort_values('Hora_Producto').reset_index(drop=True)
    estados = grp['Estado'].values
    horas = grp['Hora_Producto'].values

    for i in range(1, len(estados)):
        if estados[i] == 'CRITICO' and estados[i-1] in ['PRECAUCION', 'NORMAL']:
            transiciones.append({
                'Equipo': equipo,
                'Desde': estados[i-1],
                'Hora_transicion': horas[i],
                'Hora_anterior': horas[i-1],
                'Fecha': grp['Fecha'].iloc[i]
            })

trans_df = pd.DataFrame(transiciones)
print("Estadísticas de hora de transición a CRÍTICO:")
print(trans_df.groupby('Desde')['Hora_transicion'].describe().round(1))

# Histograma de horas de transición a crítico
fig, ax = plt.subplots(figsize=(12, 5))
ax.hist(trans_df[trans_df['Desde']=='PRECAUCION']['Hora_transicion'],
        bins=30, color='#e74c3c', alpha=0.7, edgecolor='white')
ax.set_title('Distribución de Horas de Producto al Momento de Entrar en Estado CRÍTICO\n(Transición desde PRECAUCION → CRITICO)')
ax.set_xlabel('Horas de Producto')
ax.set_ylabel('Frecuencia')
ax.axvline(trans_df['Hora_transicion'].median(), color='black', linestyle='--',
           label=f"Mediana: {trans_df['Hora_transicion'].median():.0f}h")
ax.legend()
plt.tight_layout()
plt.savefig('outputs/05_horas_critico.png', dpi=150, bbox_inches='tight')
plt.show()
```

### 7.2 — Comportamiento de variables en las últimas N muestras antes de CRÍTICO
```python
# Para cada secuencia que termina en CRÍTICO, extraer las últimas 5 muestras previas
# Calcular el promedio de cada variable en esas 5 muestras
# Comparar con el promedio general de muestras en estado NORMAL
# Esto define los "patrones de alerta temprana" (early warning signals)
# Visualizar como radar chart o heatmap de cambio %

n_previas = 5
alertas_previas = []
for equipo, grp in df.groupby('Equipo'):
    grp = grp.sort_values('Hora_Producto').reset_index(drop=True)
    criticos_idx = grp.index[grp['Estado'] == 'CRITICO'].tolist()

    for idx in criticos_idx:
        inicio = max(0, idx - n_previas)
        muestras_previas = grp.iloc[inicio:idx]
        if len(muestras_previas) >= 2:
            row = {'Equipo': equipo, 'Hora_critico': grp.loc[idx, 'Hora_Producto']}
            for var in VARS_LAG:
                if var in grp.columns:
                    row[f'prev_{var[:20]}'] = muestras_previas[var].mean()
            alertas_previas.append(row)

alertas_df = pd.DataFrame(alertas_previas)
print(f"\nSecuencias pre-crítico identificadas: {len(alertas_df)}")
```

---

## SECCIÓN 8 — PERFIL DE CADA EQUIPO (DASHBOARD RESUMEN)

```python
# Para cada equipo, generar una figura resumen (tipo "ficha técnica") con:
# Panel 1: Timeline de estados a lo largo del tiempo (barra de colores horizontal)
# Panel 2: Evolución de Hollín y TBN en el tiempo (eje X = Hora_Producto)
# Panel 3: Evolución de Hierro y Cobre
# Panel 4: Distribución de estados (pie chart)
# Panel 5: Tabla de estadísticas clave (media por estado)
# Guardar en 'outputs/perfil_{EQUIPO}.png'
# Solo hacer para los top 10 equipos

for equipo in equipos_top:
    grp = df[df['Equipo']==equipo].sort_values('Hora_Producto').copy()

    fig = plt.figure(figsize=(20, 12))
    gs = gridspec.GridSpec(3, 3, figure=fig)

    fig.suptitle(f'PERFIL DE EQUIPO: {equipo}\n'
                 f'{len(grp)} muestras | '
                 f'{grp["Fecha"].min().date()} → {grp["Fecha"].max().date()} | '
                 f'CRÍTICO: {(grp["Estado"]=="CRITICO").mean()*100:.1f}%',
                 fontsize=14, fontweight='bold')

    # Panel 1 (fila 0, toda la fila): timeline de estados
    ax1 = fig.add_subplot(gs[0, :])
    colores_num = grp['Estado'].map({'NORMAL': 1, 'PRECAUCION': 2, 'CRITICO': 3})
    cmap = plt.cm.get_cmap('RdYlGn_r', 3)
    scatter = ax1.scatter(grp['Fecha'], [1]*len(grp), c=colores_num,
                          cmap=cmap, s=100, marker='|', linewidths=3)
    ax1.set_ylim(0.5, 1.5)
    ax1.set_yticks([])
    ax1.set_title('Timeline de Estados')
    ax1.set_xlabel('Fecha')

    # Panel 2: TBN y Hollín vs horas
    ax2 = fig.add_subplot(gs[1, :2])
    ax2b = ax2.twinx()
    s = grp[['Hora_Producto', 'TBN (mg KOH/g)', 'Hollin ABS/01 mm', 'Estado']].dropna()
    for estado, color in COLORES_ESTADO.items():
        m = s['Estado'] == estado
        ax2.scatter(s.loc[m, 'Hora_Producto'], s.loc[m, 'TBN (mg KOH/g)'],
                   c=color, alpha=0.5, s=20, label=estado)
        ax2b.scatter(s.loc[m, 'Hora_Producto'], s.loc[m, 'Hollin ABS/01 mm'],
                    c=color, alpha=0.3, s=20, marker='^')
    ax2.set_title('TBN (●) y Hollín (▲) vs Horas de Producto')
    ax2.set_ylabel('TBN (mg KOH/g)', color='navy')
    ax2b.set_ylabel('Hollín ABS/01 mm', color='darkred')
    ax2.legend(fontsize=7)

    # Panel 3: Hierro y Cobre vs horas
    ax3 = fig.add_subplot(gs[2, :2])
    s2 = grp[['Hora_Producto', 'Fierro ppm', 'Cobre ppm', 'Estado']].dropna()
    for estado, color in COLORES_ESTADO.items():
        m = s2['Estado'] == estado
        ax3.scatter(s2.loc[m, 'Hora_Producto'], s2.loc[m, 'Fierro ppm'],
                   c=color, alpha=0.5, s=20)
    ax3.set_title('Fierro ppm vs Horas de Producto')
    ax3.set_ylabel('Fierro (ppm)')
    ax3.set_xlabel('Horas de Producto')

    # Panel 4: Pie chart de estados
    ax4 = fig.add_subplot(gs[1, 2])
    estado_counts = grp['Estado'].value_counts()
    ax4.pie(estado_counts.values, labels=estado_counts.index,
            colors=['#e74c3c', '#f39c12', '#2ecc71'][:len(estado_counts)],
            autopct='%1.1f%%', startangle=90)
    ax4.set_title('Distribución de Estados')

    # Panel 5: Stats clave
    ax5 = fig.add_subplot(gs[2, 2])
    ax5.axis('off')
    stats_data = []
    for var in ['Hollin ABS/01 mm', 'Fierro ppm', 'TBN (mg KOH/g)', 'Viscosidad a 100 °C cSt']:
        if var in grp.columns:
            val = pd.to_numeric(grp[var], errors='coerce')
            stats_data.append([var[:25], f"{val.mean():.2f}", f"{val.max():.2f}"])
    table = ax5.table(cellText=stats_data, colLabels=['Variable', 'Media', 'Máx'],
                     loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    ax5.set_title('Estadísticas Clave', fontsize=10)

    plt.tight_layout()
    plt.savefig(f'outputs/perfil_{equipo}.png', dpi=120, bbox_inches='tight')
    plt.show()
    plt.close()
    print(f"✓ Perfil {equipo} generado")
```

---

## SECCIÓN 9 — RESUMEN EJECUTIVO Y EXPORTACIÓN

```python
# Celda final de resumen:
# 1. Exportar a Excel un resumen con múltiples hojas:
#    - Hoja 1: sampling_df (estadísticas de muestreo por equipo)
#    - Hoja 2: adf_df (resultados de estacionariedad)
#    - Hoja 3: results_df (métricas de modelos baseline t+1)
#    - Hoja 4: trans_df (transiciones a crítico)
#    - Hoja 5: alertas_df (perfil pre-crítico)

with pd.ExcelWriter('outputs/resumen_exploracion_794AC.xlsx', engine='openpyxl') as writer:
    sampling_df.to_excel(writer, sheet_name='Muestreo_por_equipo', index=False)
    adf_df.to_excel(writer, sheet_name='Estacionariedad_ADF', index=False)
    results_df.to_excel(writer, sheet_name='Baseline_prediccion_t1', index=False)
    trans_df.to_excel(writer, sheet_name='Transiciones_critico', index=False)

print("""
╔══════════════════════════════════════════════════════════════════════╗
║         RESUMEN EJECUTIVO — EXPLORACIÓN 794AC QUELLAVECO            ║
╠══════════════════════════════════════════════════════════════════════╣
║  PREGUNTAS CLAVE QUE ESTE NOTEBOOK RESPONDE:                        ║
║                                                                      ║
║  1. ¿Cada cuánto se toman muestras?                                  ║
║     → Cada ~5-8 días / cada 80-120 horas de operación               ║
║                                                                      ║
║  2. ¿Los datos se prestan para predecir t+1?                         ║
║     → SÍ. TBN y Viscosidad tienen autocorr >0.6 (muy predecibles)   ║
║                                                                      ║
║  3. ¿A qué hora se vuelven críticos los camiones?                    ║
║     → Ver histograma Sección 7.1 y tabla de transiciones             ║
║                                                                      ║
║  4. ¿Qué variables son early warning signals?                        ║
║     → Ver análisis pre-crítico Sección 7.2                           ║
║                                                                      ║
║  5. ¿Cuáles equipos tienen peor perfil?                              ║
║     → Ver perfiles individuales (Sección 8)                          ║
║                                                                      ║
║  PRÓXIMOS PASOS PARA EL SaaS:                                        ║
║  → Fase 2: LightGBM/XGBoost con features de lag para t+1            ║
║  → Fase 3: Modelo de sobrevivencia (hours-to-critical)               ║
║  → Fase 4: API + Dashboard                                           ║
╚══════════════════════════════════════════════════════════════════════╝
""")
```

---

## NOTAS FINALES PARA CURSOR

1. **Crear carpeta de outputs:** Al inicio del notebook, agregar:
   ```python
   import os
   os.makedirs('outputs', exist_ok=True)
   ```

2. **Manejo de nulos:** Antes de graficar, siempre filtrar con `.dropna(subset=[var])`.
   No eliminar filas del dataframe principal, solo filtrar localmente para cada análisis.

3. **Cambios de aceite:** Las horas de producto se resetean a valores bajos (0-50h) cuando
   se hace un cambio de aceite. Al construir lags, verificar si `Hora_Producto < Hora_Producto_anterior`
   → eso indica cambio de aceite y el lag no debe cruzar ese límite.
   Añadir feature booleana `es_cambio_aceite = (delta_Hora_Producto < 0)`.

4. **Paleta de colores consistente:**
   ```python
   COLORES_ESTADO = {'NORMAL': '#2ecc71', 'PRECAUCION': '#f39c12', 'CRITICO': '#e74c3c'}
   ```

5. **Títulos de gráficos:** Siempre incluir n de muestras y fecha de análisis.

6. **Guardar todos los outputs:** Cada figura se guarda en `outputs/` y cada tabla importante
   se exporta al Excel `outputs/resumen_exploracion_794AC.xlsx`.

7. **El notebook debe ser auto-contenido:** Solo necesita el archivo Excel como input.
   La ruta se define en la primera celda como variable `FILE_PATH`.
