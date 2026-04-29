# PROMPT PARA CURSOR — Fase 2: Motor Predictivo del SaaS
## Flota 794AC — Mina Quellaveco

---

## CONTEXTO Y RESULTADOS DE LA FASE 1

En la Fase 1 (notebook `exploracion_ciclo_vida_794AC.ipynb`) se obtuvieron los siguientes
hallazgos clave que guían el diseño de la Fase 2:

### Hallazgos confirmados:
1. **Umbral de quiebre a ~400-450 horas** de producto: el % de muestras CRÍTICAS salta de
   22% a 43% en ese rango. Por encima de 500h, +67% son críticas.
2. **Baseline t+1 con Random Forest ya logra R² > 0.92** en todas las variables clave.
   El rolling_mean de 3 muestras es el mejor predictor individual (r=0.93 para Hollín).
3. **Ridge R²=1.000 es DATA LEAKAGE** — ocurre porque el rolling_mean calculado incluye
   datos del futuro. Hay que corregirlo en Fase 2.
4. **Early Warning Signals confirmados**: Potasio (+301%), Cobre (+161%), Hollín (+160%),
   Hierro (+137%) se disparan ANTES de que el estado se vuelva CRÍTICO.
5. **Ventana de intervención**: desde PRECAUCIÓN a CRÍTICO transcurren ~434h (mediana),
   con P25=323h y P75=521h. Hay ~100h de margen para actuar.
6. **Variables más predecibles**: Hollín (autocorr=0.806), TBN (0.534), Sulfatación (0.515),
   Hierro (0.452). Potasio y Cromo son los menos predecibles (0.06 y 0.11).

### Problema identificado a corregir:
- El cálculo de rolling_mean en Fase 1 tiene **data leakage** (usa datos del mismo punto t).
  En Fase 2, todos los features deben ser calculados usando SOLO muestras anteriores a t.

---

## OBJETIVO DE LA FASE 2

Construir el **motor predictivo completo** del SaaS con tres capacidades:

1. **Predictor de valores t+1** — dado el historial de un camión, predecir los valores
   de las variables analíticas en la próxima muestra.
2. **Clasificador de estado futuro** — predecir si el estado de la próxima muestra será
   NORMAL / PRECAUCION / CRITICO.
3. **Estimador de horas restantes** — dado el estado actual de un camión, estimar
   cuántas horas de operación faltan para que entre en estado CRÍTICO.

---

## INSTRUCCIONES PARA EL NOTEBOOK

Crea un **Jupyter Notebook Python** llamado `fase2_motor_predictivo_794AC.ipynb`.
Usa las siguientes librerías:
```python
pandas, numpy, matplotlib, seaborn, scipy, sklearn, lightgbm, xgboost,
optuna, shap, warnings, joblib
```

Instalar si no están disponibles:
```bash
pip install lightgbm xgboost optuna shap joblib
```

---

## SECCIÓN 0 — CONFIGURACIÓN

```python
import os, warnings, joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, StratifiedKFold, KFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, mean_absolute_error,
                             mean_squared_error, r2_score)
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import lightgbm as lgb
import xgboost as xgb
import optuna
import shap

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)
plt.rcParams['figure.dpi'] = 120
os.makedirs('outputs_fase2', exist_ok=True)
os.makedirs('models', exist_ok=True)

# ─── CONFIGURACIÓN PRINCIPAL ────────────────────────────────────────
FILE_PATH  = 'DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx'
SHEET_NAME = '794AC QUELLA'
N_LAGS     = 5        # Número de muestras pasadas como features
N_TRIALS   = 50       # Iteraciones de optimización Optuna (subir a 100 para producción)
RANDOM_STATE = 42

VARS_LAG = [
    'TBN (mg KOH/g)',
    'Viscosidad a 100 °C cSt',
    'Hollin ABS/01 mm',
    'Fierro ppm',
    'Oxidación ABS/01 mm',
    'Sulfatación ABS/01 mm',
    'Nitración ABS/01 mm',
    'Cobre ppm',
    'Potasio ppm',
    'Silicio ppm',
    'Aluminio ppm',
    'Cromo ppm',
]

COLORES_ESTADO = {'NORMAL': '#2ecc71', 'PRECAUCION': '#f39c12', 'CRITICO': '#e74c3c'}
```

---

## SECCIÓN 1 — CARGA Y CONSTRUCCIÓN DE FEATURES (SIN DATA LEAKAGE)

```python
# ── 1.1 Carga de datos ──────────────────────────────────────────────
df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
df['Fecha'] = pd.to_datetime(df['Fecha'])
df['Hora_Producto'] = pd.to_numeric(df['Hora_Producto'], errors='coerce')
for col in VARS_LAG:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

estado_map = {'NORMAL': 0, 'PRECAUCION': 1, 'CRITICO': 2}
df['Estado_num'] = df['Estado'].map(estado_map)
df = df.sort_values(['Equipo', 'Hora_Producto']).reset_index(drop=True)

print(f"Dataset cargado: {df.shape}")
print(f"Distribución de estados:\n{df['Estado'].value_counts(normalize=True).mul(100).round(1)}")

# ── 1.2 Construcción de features SIN data leakage ───────────────────
# REGLA CRÍTICA: todos los features de la muestra t deben calcularse
# EXCLUSIVAMENTE con datos de t-1, t-2, ... t-N (muestras anteriores).
# NO usar t en ningún cálculo de feature.

def build_features(df, vars_lag, n_lags):
    """
    Construye el dataset de features para predicción t+1.
    Para cada muestra t, genera:
      - lag_k_{var}: valor de la variable en t-k (k=1..n_lags)
      - delta_k_{var}: diferencia entre t-k y t-(k+1)
      - roll_mean_k_{var}: rolling mean de las últimas k muestras ANTES de t
      - roll_std_k_{var}: rolling std de las últimas k muestras ANTES de t
      - roll_trend_{var}: pendiente de regresión lineal sobre las últimas 3 muestras
      - horas_desde_ultima: delta de Hora_Producto entre t y t-1
      - es_cambio_aceite: 1 si Hora_Producto de t-1 > Hora_Producto de t (reset)
      - estado_lag1, estado_lag2: estado codificado de t-1 y t-2
      - horas_actuales: Hora_Producto en t (el "nivel de envejecimiento" actual)
    """
    dfs = []
    for equipo, grp in df.groupby('Equipo'):
        grp = grp.sort_values('Hora_Producto').copy().reset_index(drop=True)
        feat = grp[['Equipo', 'Fecha', 'Hora_Producto', 'Estado', 'Estado_num']].copy()

        for var in vars_lag:
            if var not in grp.columns:
                continue
            s = grp[var]

            # Lags (shift hacia adelante: t usa el valor de t-1)
            for k in range(1, n_lags + 1):
                feat[f'lag{k}_{var[:18]}'] = s.shift(k)

            # Deltas entre lags consecutivos (tasa de cambio)
            for k in range(1, n_lags):
                feat[f'delta{k}_{var[:18]}'] = s.shift(k) - s.shift(k + 1)

            # Rolling mean y std de las últimas 3 y 5 muestras PREVIAS
            # shift(1) asegura que t NO está incluido en el cálculo
            for w in [3, 5]:
                feat[f'rollmean{w}_{var[:15]}'] = s.shift(1).rolling(w, min_periods=2).mean()
                feat[f'rollstd{w}_{var[:15]}']  = s.shift(1).rolling(w, min_periods=2).std()

            # Tendencia lineal (pendiente) de las últimas 3 muestras previas
            def lin_slope(x):
                if x.notna().sum() < 2:
                    return np.nan
                xi = np.arange(len(x))
                valid = x.notna()
                if valid.sum() < 2:
                    return np.nan
                return np.polyfit(xi[valid], x.values[valid], 1)[0]

            feat[f'trend_{var[:18]}'] = (
                s.shift(1).rolling(3, min_periods=2).apply(lin_slope, raw=False)
            )

        # Features de contexto
        feat['horas_desde_ultima'] = grp['Hora_Producto'].diff()
        feat['es_cambio_aceite']   = (feat['horas_desde_ultima'] < 0).astype(int)
        feat['estado_lag1']        = grp['Estado_num'].shift(1)
        feat['estado_lag2']        = grp['Estado_num'].shift(2)
        feat['horas_actuales']     = grp['Hora_Producto']

        dfs.append(feat)

    return pd.concat(dfs, ignore_index=True)

df_feat = build_features(df, VARS_LAG, N_LAGS)

# Eliminar filas donde no hay suficientes lags (primeras N filas de cada equipo)
min_lag_col = f'lag{N_LAGS}_{VARS_LAG[0][:18]}'
df_feat = df_feat.dropna(subset=[min_lag_col]).reset_index(drop=True)

# Identificar columnas de features (excluir metadatos)
meta_cols  = ['Equipo', 'Fecha', 'Hora_Producto', 'Estado', 'Estado_num']
feat_cols  = [c for c in df_feat.columns if c not in meta_cols]

print(f"\nDataset con features: {df_feat.shape}")
print(f"Features construidas: {len(feat_cols)}")
print(f"Muestras válidas por equipo:")
print(df_feat.groupby('Equipo').size().sort_values(ascending=False).head(10))
```

---

## SECCIÓN 2 — MODELO A: CLASIFICADOR DE ESTADO FUTURO

> Predice si el **estado de la próxima muestra** (t+1) será NORMAL / PRECAUCION / CRITICO.
> Variable target: Estado de t (que es el "t+1" respecto a los features de t-1..t-N).

```python
# ── 2.1 Preparar datos de clasificación ─────────────────────────────
X_clf = df_feat[feat_cols].copy()
y_clf = df_feat['Estado_num'].values   # 0=CRITICO, 1=NORMAL, 2=PRECAUCION
label_names = ['CRITICO', 'NORMAL', 'PRECAUCION']

# Imputar nulos restantes con mediana
X_clf = X_clf.fillna(X_clf.median())

# Split TEMPORAL (80/20) — no shuffle, respetar el orden cronológico
split_idx = int(len(X_clf) * 0.80)
X_train_c, X_test_c = X_clf.iloc[:split_idx], X_clf.iloc[split_idx:]
y_train_c, y_test_c = y_clf[:split_idx], y_clf[split_idx:]

print(f"Train: {len(X_train_c)} muestras | Test: {len(X_test_c)} muestras")
print(f"Distribución de estados en test:")
for i, name in enumerate(label_names):
    print(f"  {name}: {(y_test_c == i).sum()}")

# ── 2.2 LightGBM con optimización Optuna ────────────────────────────
def objective_lgb_clf(trial):
    params = {
        'objective':        'multiclass',
        'num_class':        3,
        'metric':           'multi_logloss',
        'verbosity':        -1,
        'boosting_type':    'gbdt',
        'n_estimators':     trial.suggest_int('n_estimators', 100, 600),
        'max_depth':        trial.suggest_int('max_depth', 3, 10),
        'learning_rate':    trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'num_leaves':       trial.suggest_int('num_leaves', 15, 127),
        'subsample':        trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'min_child_samples':trial.suggest_int('min_child_samples', 5, 50),
        'reg_alpha':        trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda':       trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'class_weight':     'balanced',
        'random_state':     RANDOM_STATE,
        'n_jobs':           -1,
    }
    cv = StratifiedKFold(n_splits=5, shuffle=False)
    scores = []
    for tr_idx, val_idx in cv.split(X_train_c, y_train_c):
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train_c.iloc[tr_idx], y_train_c[tr_idx],
                  eval_set=[(X_train_c.iloc[val_idx], y_train_c[val_idx])],
                  callbacks=[lgb.early_stopping(30, verbose=False)])
        preds = model.predict(X_train_c.iloc[val_idx])
        scores.append(accuracy_score(y_train_c[val_idx], preds))
    return np.mean(scores)

print("\nOptimizando LightGBM (clasificador de estado)...")
study_lgb_clf = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
study_lgb_clf.optimize(objective_lgb_clf, n_trials=N_TRIALS, show_progress_bar=True)

best_params_lgb_clf = study_lgb_clf.best_params
best_params_lgb_clf.update({'objective': 'multiclass', 'num_class': 3,
                            'class_weight': 'balanced', 'random_state': RANDOM_STATE,
                            'verbosity': -1, 'n_jobs': -1})

lgb_clf = lgb.LGBMClassifier(**best_params_lgb_clf)
lgb_clf.fit(X_train_c, y_train_c)
y_pred_lgb = lgb_clf.predict(X_test_c)
acc_lgb = accuracy_score(y_test_c, y_pred_lgb)

print(f"\n✓ LightGBM Accuracy: {acc_lgb:.4f}")
print(f"  Mejores hiperparámetros: {study_lgb_clf.best_params}")
print("\nReporte de Clasificación (LightGBM):")
print(classification_report(y_test_c, y_pred_lgb, target_names=label_names))

# ── 2.3 XGBoost como comparación ────────────────────────────────────
def objective_xgb_clf(trial):
    params = {
        'objective':         'multi:softmax',
        'num_class':         3,
        'eval_metric':       'mlogloss',
        'n_estimators':      trial.suggest_int('n_estimators', 100, 500),
        'max_depth':         trial.suggest_int('max_depth', 3, 8),
        'learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample':         trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree':  trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'min_child_weight':  trial.suggest_int('min_child_weight', 1, 10),
        'gamma':             trial.suggest_float('gamma', 0, 5),
        'reg_alpha':         trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda':        trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'random_state':      RANDOM_STATE,
        'use_label_encoder': False,
        'verbosity':         0,
        'n_jobs':            -1,
    }
    cv = StratifiedKFold(n_splits=5, shuffle=False)
    scores = []
    for tr_idx, val_idx in cv.split(X_train_c, y_train_c):
        model = xgb.XGBClassifier(**params)
        model.fit(X_train_c.iloc[tr_idx], y_train_c[tr_idx], verbose=False)
        preds = model.predict(X_train_c.iloc[val_idx])
        scores.append(accuracy_score(y_train_c[val_idx], preds))
    return np.mean(scores)

print("\nOptimizando XGBoost (clasificador de estado)...")
study_xgb_clf = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
study_xgb_clf.optimize(objective_xgb_clf, n_trials=N_TRIALS, show_progress_bar=True)

best_params_xgb_clf = study_xgb_clf.best_params
best_params_xgb_clf.update({'objective': 'multi:softmax', 'num_class': 3,
                            'use_label_encoder': False, 'verbosity': 0,
                            'random_state': RANDOM_STATE, 'n_jobs': -1})

xgb_clf = xgb.XGBClassifier(**best_params_xgb_clf)
xgb_clf.fit(X_train_c, y_train_c)
y_pred_xgb = xgb_clf.predict(X_test_c)
acc_xgb = accuracy_score(y_test_c, y_pred_xgb)

print(f"\n✓ XGBoost Accuracy: {acc_xgb:.4f}")
print("\nReporte de Clasificación (XGBoost):")
print(classification_report(y_test_c, y_pred_xgb, target_names=label_names))

# ── 2.4 Comparación y matriz de confusión ───────────────────────────
print(f"\n{'='*50}")
print(f" COMPARACIÓN DE MODELOS (Clasificación de Estado)")
print(f"{'='*50}")
print(f"  LightGBM: {acc_lgb:.4f}")
print(f"  XGBoost:  {acc_xgb:.4f}")
best_clf = lgb_clf if acc_lgb >= acc_xgb else xgb_clf
best_clf_name = 'LightGBM' if acc_lgb >= acc_xgb else 'XGBoost'
y_pred_best_clf = y_pred_lgb if acc_lgb >= acc_xgb else y_pred_xgb
print(f"  → Mejor modelo: {best_clf_name}")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for ax, y_pred, title in zip(axes, [y_pred_lgb, y_pred_xgb], ['LightGBM', 'XGBoost']):
    cm = confusion_matrix(y_test_c, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=label_names, yticklabels=label_names, ax=ax)
    ax.set_title(f'Matriz de Confusión — {title}\nAccuracy: {accuracy_score(y_test_c, y_pred):.4f}')
    ax.set_xlabel('Predicho')
    ax.set_ylabel('Real')
plt.tight_layout()
plt.savefig('outputs_fase2/01_confusion_matrix_clasificacion.png', dpi=150, bbox_inches='tight')
plt.show()

# Guardar el mejor modelo de clasificación
joblib.dump(best_clf, f'models/clasificador_estado_{best_clf_name.lower()}.pkl')
print(f"✓ Modelo guardado: models/clasificador_estado_{best_clf_name.lower()}.pkl")
```

---

## SECCIÓN 3 — MODELO B: REGRESOR DE VARIABLES t+1

> Predice los **valores numéricos** de las variables analíticas en la próxima muestra.
> Se entrena un modelo por variable (LightGBM Regressor + Optuna).

```python
# ── 3.1 Función de optimización para regresor LightGBM ──────────────
def optimize_lgb_regressor(X_tr, y_tr, n_trials):
    def objective(trial):
        params = {
            'objective':         'regression',
            'metric':            'mae',
            'verbosity':         -1,
            'n_estimators':      trial.suggest_int('n_estimators', 100, 600),
            'max_depth':         trial.suggest_int('max_depth', 3, 10),
            'learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'num_leaves':        trial.suggest_int('num_leaves', 15, 127),
            'subsample':         trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree':  trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
            'reg_alpha':         trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            'reg_lambda':        trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            'random_state':      RANDOM_STATE,
            'n_jobs':            -1,
        }
        kf = KFold(n_splits=5, shuffle=False)
        maes = []
        for tr_idx, val_idx in kf.split(X_tr):
            model = lgb.LGBMRegressor(**params)
            model.fit(X_tr.iloc[tr_idx], y_tr[tr_idx],
                      eval_set=[(X_tr.iloc[val_idx], y_tr[val_idx])],
                      callbacks=[lgb.early_stopping(30, verbose=False)])
            preds = model.predict(X_tr.iloc[val_idx])
            maes.append(mean_absolute_error(y_tr[val_idx], preds))
        return np.mean(maes)

    study = optuna.create_study(direction='minimize',
                                sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study.best_params

# ── 3.2 Entrenar un regresor por variable ───────────────────────────
regression_results = []
regression_models  = {}

print("="*65)
print(" REGRESIÓN t+1 — LightGBM optimizado por variable")
print("="*65)

for var in VARS_LAG:
    if var not in df_feat.columns:
        continue

    # Target: valor actual de la variable (que es t+1 respecto a los features)
    y_reg = df_feat[var].values

    # Mask: eliminar filas donde el target es nulo
    valid_mask = ~np.isnan(y_reg)
    X_reg = X_clf[valid_mask].copy()
    y_reg = y_reg[valid_mask]

    if len(y_reg) < 200:
        print(f"  ⚠ {var[:30]}: insuficientes muestras ({len(y_reg)}), saltando.")
        continue

    # Split temporal 80/20
    split = int(len(X_reg) * 0.80)
    X_tr, X_te = X_reg.iloc[:split], X_reg.iloc[split:]
    y_tr, y_te = y_reg[:split], y_reg[split:]

    # Optimizar hiperparámetros
    best_hp = optimize_lgb_regressor(X_tr, y_tr, N_TRIALS)
    best_hp.update({'objective': 'regression', 'verbosity': -1,
                    'random_state': RANDOM_STATE, 'n_jobs': -1})

    model = lgb.LGBMRegressor(**best_hp)
    model.fit(X_tr, y_tr)
    y_pred = model.predict(X_te)

    mae  = mean_absolute_error(y_te, y_pred)
    rmse = np.sqrt(mean_squared_error(y_te, y_pred))
    r2   = r2_score(y_te, y_pred)

    # Calcular MAPE (error % relativo)
    mape = np.mean(np.abs((y_te - y_pred) / (np.abs(y_te) + 1e-8))) * 100

    regression_results.append({
        'Variable': var, 'MAE': round(mae, 4), 'RMSE': round(rmse, 4),
        'R2': round(r2, 4), 'MAPE_%': round(mape, 2), 'N_test': len(y_te)
    })
    regression_models[var] = model

    print(f"  ✓ {var[:30]:30s} → MAE={mae:.4f} | RMSE={rmse:.4f} | R²={r2:.4f} | MAPE={mape:.1f}%")

    # Guardar modelo
    safe_name = var.replace(' ', '_').replace('/', '_').replace('°', 'deg')[:30]
    joblib.dump(model, f'models/regresor_{safe_name}.pkl')

reg_df = pd.DataFrame(regression_results)
print(f"\n{'='*65}")
print("Resumen de regresores:")
print(reg_df.to_string(index=False))
reg_df.to_excel('outputs_fase2/02_resultados_regresion_t1.xlsx', index=False)
```

---

## SECCIÓN 4 — ANÁLISIS SHAP (INTERPRETABILIDAD)

```python
# ── 4.1 SHAP para el clasificador de estado ─────────────────────────
print("Calculando SHAP values para el clasificador de estado...")

# Usar una muestra del test set para SHAP (máx 500 filas por velocidad)
X_shap = X_test_c.sample(min(500, len(X_test_c)), random_state=RANDOM_STATE)

if best_clf_name == 'LightGBM':
    explainer = shap.TreeExplainer(best_clf)
    shap_values = explainer.shap_values(X_shap)
else:
    explainer = shap.TreeExplainer(best_clf)
    shap_values = explainer.shap_values(X_shap)

# Plot SHAP summary (importancia global)
fig, ax = plt.subplots(figsize=(12, 10))
if isinstance(shap_values, list):
    shap_abs = np.sum([np.abs(sv) for sv in shap_values], axis=0)
    shap.summary_plot(shap_abs, X_shap, plot_type='bar',
                      feature_names=feat_cols, show=False, max_display=25)
else:
    shap.summary_plot(shap_values, X_shap, plot_type='bar',
                      feature_names=feat_cols, show=False, max_display=25)
plt.title(f'Importancia SHAP Global — Clasificador de Estado ({best_clf_name})', fontsize=13)
plt.tight_layout()
plt.savefig('outputs_fase2/03_shap_clasificador.png', dpi=150, bbox_inches='tight')
plt.show()

# SHAP por clase
if isinstance(shap_values, list):
    class_names_shap = ['CRITICO', 'NORMAL', 'PRECAUCION']
    fig, axes = plt.subplots(1, 3, figsize=(22, 8))
    for i, (sv, cname) in enumerate(zip(shap_values, class_names_shap)):
        shap_imp = pd.DataFrame({
            'Feature': feat_cols,
            'SHAP_mean_abs': np.abs(sv).mean(axis=0)
        }).sort_values('SHAP_mean_abs', ascending=False).head(15)

        axes[i].barh(range(15), shap_imp['SHAP_mean_abs'].values[::-1], color=list(COLORES_ESTADO.values())[i])
        axes[i].set_yticks(range(15))
        axes[i].set_yticklabels(shap_imp['Feature'].values[::-1], fontsize=8)
        axes[i].set_title(f'SHAP Top 15 — Clase {cname}', fontsize=10)
        axes[i].set_xlabel('|SHAP| medio')
    plt.tight_layout()
    plt.savefig('outputs_fase2/04_shap_por_clase.png', dpi=150, bbox_inches='tight')
    plt.show()

# ── 4.2 Top features según SHAP — tabla resumen ─────────────────────
if isinstance(shap_values, list):
    global_shap = np.sum([np.abs(sv) for sv in shap_values], axis=0).mean(axis=0)
else:
    global_shap = np.abs(shap_values).mean(axis=0)

shap_ranking = pd.DataFrame({
    'Feature': feat_cols,
    'SHAP_importancia': global_shap
}).sort_values('SHAP_importancia', ascending=False).head(30)

print("\nTop 30 features más importantes (SHAP global):")
print(shap_ranking.to_string(index=False))
shap_ranking.to_excel('outputs_fase2/05_shap_ranking.xlsx', index=False)
```

---

## SECCIÓN 5 — MODELO C: ESTIMADOR DE HORAS RESTANTES HASTA CRÍTICO

> Responde: "¿Cuántas horas de operación le quedan a este camión antes de entrar en CRÍTICO?"
> Enfoque: regresión sobre el tiempo restante hasta la primera transición a CRÍTICO.

```python
# ── 5.1 Construir target: horas restantes hasta CRÍTICO ─────────────
# Para cada muestra que NO es CRÍTICA, calcular cuántas horas
# de Hora_Producto faltan hasta que el equipo entre en estado CRITICO.
# Si no hay transición a CRITICO siguiente, el target es NaN (censurado).

def compute_horas_hasta_critico(df):
    rows = []
    for equipo, grp in df.groupby('Equipo'):
        grp = grp.sort_values('Hora_Producto').reset_index(drop=True)
        for i, row in grp.iterrows():
            if row['Estado'] == 'CRITICO':
                continue
            # Buscar la próxima muestra CRITICA en la secuencia
            futuros_criticos = grp.loc[grp.index > i][grp.loc[grp.index > i]['Estado'] == 'CRITICO']
            if len(futuros_criticos) == 0:
                horas_restantes = np.nan   # censurado
            else:
                primera_critica = futuros_criticos.iloc[0]
                horas_restantes = primera_critica['Hora_Producto'] - row['Hora_Producto']
                if horas_restantes < 0:
                    horas_restantes = np.nan
            rows.append({
                'Equipo': row['Equipo'],
                'Fecha': row['Fecha'],
                'Hora_Producto': row['Hora_Producto'],
                'Estado': row['Estado'],
                'Horas_hasta_critico': horas_restantes
            })
    return pd.DataFrame(rows)

print("Calculando horas hasta próximo estado CRÍTICO...")
df_survival = compute_horas_hasta_critico(df)
df_survival = df_survival.dropna(subset=['Horas_hasta_critico'])

print(f"Muestras válidas para survival: {len(df_survival)}")
print(f"Estadísticas de horas restantes:")
print(df_survival['Horas_hasta_critico'].describe().round(1))

# Histograma de horas restantes
fig, ax = plt.subplots(figsize=(12, 5))
ax.hist(df_survival['Horas_hasta_critico'], bins=40,
        color='#e74c3c', alpha=0.7, edgecolor='white')
ax.axvline(df_survival['Horas_hasta_critico'].median(), color='black',
           linestyle='--', label=f"Mediana: {df_survival['Horas_hasta_critico'].median():.0f}h")
ax.set_title('Distribución de Horas Restantes Hasta Estado CRÍTICO')
ax.set_xlabel('Horas de Producto restantes')
ax.set_ylabel('Frecuencia')
ax.legend()
plt.tight_layout()
plt.savefig('outputs_fase2/06_horas_restantes_distribucion.png', dpi=150, bbox_inches='tight')
plt.show()

# ── 5.2 Merge con features y entrenar regresor de supervivencia ──────
# Unir df_survival con df_feat por Equipo + Fecha
df_surv_feat = df_survival.merge(
    df_feat[['Equipo', 'Fecha'] + feat_cols],
    on=['Equipo', 'Fecha'], how='inner'
).dropna(subset=feat_cols[:10])

X_surv = df_surv_feat[feat_cols].fillna(df_surv_feat[feat_cols].median())
y_surv = df_surv_feat['Horas_hasta_critico'].values

split = int(len(X_surv) * 0.80)
X_tr_s, X_te_s = X_surv.iloc[:split], X_surv.iloc[split:]
y_tr_s, y_te_s = y_surv[:split], y_surv[split:]

# Modelo de supervivencia con LightGBM Regressor
surv_params = {
    'objective': 'regression', 'metric': 'mae', 'verbosity': -1,
    'n_estimators': 400, 'max_depth': 6, 'learning_rate': 0.05,
    'num_leaves': 63, 'subsample': 0.8, 'colsample_bytree': 0.8,
    'random_state': RANDOM_STATE, 'n_jobs': -1
}
surv_model = lgb.LGBMRegressor(**surv_params)
surv_model.fit(X_tr_s, y_tr_s)
y_pred_surv = surv_model.predict(X_te_s)

mae_surv  = mean_absolute_error(y_te_s, y_pred_surv)
rmse_surv = np.sqrt(mean_squared_error(y_te_s, y_pred_surv))
r2_surv   = r2_score(y_te_s, y_pred_surv)

print(f"\n✓ Modelo de Supervivencia (Horas hasta CRÍTICO):")
print(f"  MAE:  {mae_surv:.1f} horas")
print(f"  RMSE: {rmse_surv:.1f} horas")
print(f"  R²:   {r2_surv:.4f}")

joblib.dump(surv_model, 'models/estimador_horas_hasta_critico.pkl')

# Predicción vs Real (scatter)
fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(y_te_s, y_pred_surv, alpha=0.3, c='steelblue', s=20)
lim = [0, max(y_te_s.max(), y_pred_surv.max())]
ax.plot(lim, lim, 'r--', linewidth=1.5, label='Predicción perfecta')
ax.set_xlabel('Horas Reales hasta CRÍTICO')
ax.set_ylabel('Horas Predichas hasta CRÍTICO')
ax.set_title(f'Predicción vs Real — Horas hasta CRÍTICO\nMAE={mae_surv:.1f}h | R²={r2_surv:.4f}')
ax.legend()
plt.tight_layout()
plt.savefig('outputs_fase2/07_supervivencia_pred_vs_real.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## SECCIÓN 6 — EVALUACIÓN POR EQUIPO

```python
# ── 6.1 Accuracy del clasificador por equipo individual ─────────────
# Evaluar si el modelo funciona bien en todos los camiones o si hay
# algunos equipos donde las predicciones son sistemáticamente peores.

print("\n" + "="*60)
print(" ACCURACY DEL CLASIFICADOR POR EQUIPO")
print("="*60)

test_data = df_feat.iloc[split_idx:].copy()
test_data['y_pred_clf'] = y_pred_best_clf
test_data['y_real_clf'] = y_test_c

per_equipo = []
for equipo, grp in test_data.groupby('Equipo'):
    if len(grp) < 5:
        continue
    acc = accuracy_score(grp['y_real_clf'], grp['y_pred_clf'])
    n_critico_real  = (grp['y_real_clf'] == 0).sum()
    n_critico_pred  = (grp['y_pred_clf'] == 0).sum()
    per_equipo.append({
        'Equipo': equipo, 'N': len(grp),
        'Accuracy': round(acc, 4),
        'CRITICO_real': n_critico_real,
        'CRITICO_pred': n_critico_pred,
    })

per_equipo_df = pd.DataFrame(per_equipo).sort_values('Accuracy')
print(per_equipo_df.to_string(index=False))

# Gráfico de barras: accuracy por equipo
fig, ax = plt.subplots(figsize=(14, 5))
colors = ['#e74c3c' if a < 0.85 else '#f39c12' if a < 0.92 else '#2ecc71'
          for a in per_equipo_df['Accuracy']]
ax.bar(per_equipo_df['Equipo'], per_equipo_df['Accuracy'], color=colors, edgecolor='white')
ax.axhline(0.90, color='orange', linestyle='--', label='Umbral 90%')
ax.axhline(0.95, color='green', linestyle='--', label='Umbral 95%')
ax.set_ylim(0.5, 1.05)
ax.set_title('Accuracy del Clasificador de Estado por Equipo')
ax.set_xlabel('Equipo')
ax.set_ylabel('Accuracy')
ax.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('outputs_fase2/08_accuracy_por_equipo.png', dpi=150, bbox_inches='tight')
plt.show()

# ── 6.2 Simulación de predicción para un equipo específico ───────────
# Para HT012 y HT001, simular cómo hubiera predicho el modelo en tiempo real:
# En cada punto t, tomar los features disponibles y predecir:
# - Estado de la próxima muestra
# - Horas restantes hasta CRÍTICO
# Graficar la línea de tiempo con predicciones vs real.

for equipo_demo in ['HT012', 'HT001']:
    grp_demo = test_data[test_data['Equipo'] == equipo_demo].copy()
    if len(grp_demo) < 5:
        continue

    grp_demo['estado_pred_nombre'] = grp_demo['y_pred_clf'].map(
        {0: 'CRITICO', 1: 'NORMAL', 2: 'PRECAUCION'})
    grp_demo['estado_real_nombre'] = grp_demo['y_real_clf'].map(
        {0: 'CRITICO', 1: 'NORMAL', 2: 'PRECAUCION'})

    fig, axes = plt.subplots(2, 1, figsize=(16, 8))
    fig.suptitle(f'Simulación en Tiempo Real — {equipo_demo}', fontsize=13, fontweight='bold')

    # Panel superior: predicción vs real por muestra
    x = range(len(grp_demo))
    axes[0].plot(x, grp_demo['y_real_clf'].values, 'o-', color='navy',
                 markersize=5, label='Estado Real', linewidth=1.5)
    axes[0].plot(x, grp_demo['y_pred_clf'].values, 's--', color='tomato',
                 markersize=5, label='Estado Predicho', linewidth=1.5)
    axes[0].set_yticks([0, 1, 2])
    axes[0].set_yticklabels(['CRÍTICO', 'NORMAL', 'PRECAUCIÓN'])
    axes[0].set_title('Predicción de Estado vs Real')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Panel inferior: Hora_Producto en el tiempo
    axes[1].plot(x, grp_demo['Hora_Producto'].values, 'b-o', markersize=4)
    axes[1].axhline(400, color='orange', linestyle='--', alpha=0.7, label='400h (zona riesgo)')
    axes[1].axhline(500, color='red', linestyle='--', alpha=0.7, label='500h (zona crítica)')
    axes[1].set_title('Horas de Producto a lo largo del test')
    axes[1].set_xlabel('Índice de muestra')
    axes[1].set_ylabel('Horas de Producto')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'outputs_fase2/09_simulacion_{equipo_demo}.png', dpi=150, bbox_inches='tight')
    plt.show()
```

---

## SECCIÓN 7 — FUNCIÓN DE PREDICCIÓN EN PRODUCCIÓN

```python
# ── 7.1 Función predict_next_sample ─────────────────────────────────
# Esta es la función que irá en el backend del SaaS.
# Input:  DataFrame con el historial de un equipo (mínimo N_LAGS muestras)
# Output: dict con predicciones de estado, valores t+1 y horas restantes.

def predict_next_sample(historial_equipo: pd.DataFrame,
                        clasificador,
                        regresores: dict,
                        surv_model,
                        vars_lag: list,
                        n_lags: int = 5) -> dict:
    """
    Genera predicciones para la próxima muestra de un equipo.

    Args:
        historial_equipo: DataFrame con las últimas N muestras del equipo,
                          ordenado por Hora_Producto ascendente.
                          Debe contener columnas: Hora_Producto, Estado, + vars_lag
        clasificador: modelo entrenado de clasificación de estado
        regresores: dict {variable: modelo_regresor}
        surv_model: modelo de horas hasta crítico
        vars_lag: lista de variables a predecir
        n_lags: número de lags usados en el entrenamiento

    Returns:
        dict con claves:
          - estado_predicho: 'NORMAL' | 'PRECAUCION' | 'CRITICO'
          - probabilidades_estado: {clase: probabilidad}
          - valores_predichos: {variable: valor_predicho}
          - horas_restantes_hasta_critico: float o None
          - nivel_alerta: 'VERDE' | 'AMARILLO' | 'ROJO'
          - mensaje: str con recomendación
    """
    if len(historial_equipo) < n_lags:
        return {'error': f'Se necesitan al menos {n_lags} muestras previas'}

    grp = historial_equipo.sort_values('Hora_Producto').tail(n_lags + 2)
    estado_map_inv = {0: 'CRITICO', 1: 'NORMAL', 2: 'PRECAUCION'}
    estado_map     = {'NORMAL': 1, 'PRECAUCION': 2, 'CRITICO': 0}

    # Construir vector de features para la predicción
    features = {}
    for var in vars_lag:
        if var not in grp.columns:
            continue
        s = grp[var].values
        for k in range(1, n_lags + 1):
            idx = -(k)
            features[f'lag{k}_{var[:18]}'] = s[idx] if abs(idx) <= len(s) else np.nan
        for k in range(1, n_lags):
            features[f'delta{k}_{var[:18]}'] = (
                s[-(k)] - s[-(k+1)] if len(s) >= k+1 else np.nan
            )
        recent = grp[var].values[-min(5, len(grp)):]
        for w in [3, 5]:
            window = recent[-w:] if len(recent) >= w else recent
            features[f'rollmean{w}_{var[:15]}'] = np.nanmean(window) if len(window) > 0 else np.nan
            features[f'rollstd{w}_{var[:15]}']  = np.nanstd(window) if len(window) > 1 else 0.0
        if len(recent) >= 2:
            xi = np.arange(len(recent))
            valid = ~np.isnan(recent)
            features[f'trend_{var[:18]}'] = np.polyfit(xi[valid], recent[valid], 1)[0] if valid.sum() >= 2 else np.nan
        else:
            features[f'trend_{var[:18]}'] = np.nan

    # Hora y estado
    features['horas_actuales']    = grp['Hora_Producto'].iloc[-1]
    features['horas_desde_ultima'] = grp['Hora_Producto'].iloc[-1] - grp['Hora_Producto'].iloc[-2] if len(grp) >= 2 else np.nan
    features['es_cambio_aceite']  = 0
    estados_nums = grp['Estado'].map(estado_map)
    features['estado_lag1'] = estados_nums.iloc[-1] if len(estados_nums) >= 1 else np.nan
    features['estado_lag2'] = estados_nums.iloc[-2] if len(estados_nums) >= 2 else np.nan

    X_pred = pd.DataFrame([features])

    # Rellenar columnas faltantes con 0
    for col in feat_cols:
        if col not in X_pred.columns:
            X_pred[col] = 0.0
    X_pred = X_pred[feat_cols].fillna(0)

    # Predicción de estado
    estado_cod = clasificador.predict(X_pred)[0]
    estado_nombre = estado_map_inv.get(int(estado_cod), 'DESCONOCIDO')

    proba = {}
    if hasattr(clasificador, 'predict_proba'):
        probs = clasificador.predict_proba(X_pred)[0]
        proba = {estado_map_inv[i]: round(float(p), 4) for i, p in enumerate(probs)}

    # Predicción de valores t+1
    valores_pred = {}
    for var, reg_model in regresores.items():
        try:
            val = reg_model.predict(X_pred)[0]
            valores_pred[var] = round(float(val), 4)
        except:
            valores_pred[var] = None

    # Estimación de horas hasta crítico
    try:
        horas_critico = float(surv_model.predict(X_pred)[0])
        horas_critico = max(0, horas_critico)
    except:
        horas_critico = None

    # Nivel de alerta semafórico
    if estado_nombre == 'CRITICO' or (horas_critico is not None and horas_critico < 100):
        nivel_alerta = 'ROJO'
        mensaje = ('⚠️ ALERTA CRÍTICA: Se predice estado CRÍTICO en la próxima muestra. '
                   'Revisar inmediatamente. Considerar cambio de aceite anticipado.')
    elif estado_nombre == 'PRECAUCION' or (horas_critico is not None and horas_critico < 250):
        nivel_alerta = 'AMARILLO'
        mensaje = ('⚡ PRECAUCIÓN: El aceite está en zona de degradación avanzada. '
                   f'Horas estimadas hasta estado crítico: {horas_critico:.0f}h. '
                   'Aumentar frecuencia de muestreo.')
    else:
        nivel_alerta = 'VERDE'
        mensaje = ('✅ NORMAL: El aceite está en buen estado. '
                   'Continuar con el plan de muestreo regular.')

    return {
        'estado_predicho': estado_nombre,
        'probabilidades_estado': proba,
        'valores_predichos_t1': valores_pred,
        'horas_restantes_hasta_critico': round(horas_critico, 1) if horas_critico else None,
        'nivel_alerta': nivel_alerta,
        'mensaje': mensaje
    }

# ── 7.2 Demo de la función con datos reales ─────────────────────────
print("\n" + "="*60)
print(" DEMO: Predicción en Tiempo Real")
print("="*60)

for equipo_demo in ['HT012', 'HT001', 'HT009']:
    historial = df[df['Equipo'] == equipo_demo].sort_values('Hora_Producto').tail(10)
    if len(historial) >= N_LAGS:
        resultado = predict_next_sample(
            historial_equipo=historial,
            clasificador=best_clf,
            regresores=regression_models,
            surv_model=surv_model,
            vars_lag=VARS_LAG,
            n_lags=N_LAGS
        )
        print(f"\n  Equipo {equipo_demo} (última hora: {historial['Hora_Producto'].iloc[-1]}h):")
        print(f"  Estado actual:           {historial['Estado'].iloc[-1]}")
        print(f"  Estado predicho (t+1):   {resultado['estado_predicho']}")
        print(f"  Probabilidades:          {resultado['probabilidades_estado']}")
        print(f"  Horas hasta CRÍTICO:     {resultado['horas_restantes_hasta_critico']}h")
        print(f"  Nivel de alerta:         {resultado['nivel_alerta']}")
        print(f"  Mensaje: {resultado['mensaje'][:80]}...")
        print(f"  Valores predichos t+1:")
        for var, val in list(resultado['valores_predichos_t1'].items())[:5]:
            print(f"    {var[:30]:30s}: {val}")
```

---

## SECCIÓN 8 — EXPORTACIÓN FINAL

```python
# ── 8.1 Exportar todos los modelos ──────────────────────────────────
print("\n✓ Modelos exportados en 'models/':")
for f in os.listdir('models'):
    size = os.path.getsize(f'models/{f}') / 1024
    print(f"  📦 {f} ({size:.1f} KB)")

# ── 8.2 Resumen ejecutivo final ──────────────────────────────────────
print(f"""
╔══════════════════════════════════════════════════════════════════╗
║       RESUMEN EJECUTIVO — FASE 2 MOTOR PREDICTIVO 794AC         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  MODELOS ENTRENADOS:                                             ║
║  ✓ Clasificador de Estado (LightGBM/XGBoost + Optuna)            ║
║  ✓ Regresores t+1 por variable ({len(regression_models)} modelos LightGBM)         ║
║  ✓ Estimador de Horas hasta CRÍTICO (supervivencia)              ║
║                                                                  ║
║  CAPACIDADES DEL SISTEMA:                                        ║
║  → Predecir si la próxima muestra será NORMAL/PRECAUCIÓN/CRÍTICO ║
║  → Estimar los valores numéricos de la próxima muestra           ║
║  → Estimar cuántas horas quedan antes del estado CRÍTICO         ║
║  → Generar alertas semafóricas (VERDE / AMARILLO / ROJO)         ║
║  → Funcionar con mínimo {N_LAGS} muestras de historial del camión        ║
║                                                                  ║
║  HALLAZGO CLAVE:                                                 ║
║  La "hora de quiebre" crítica es ~400-450h de producto.          ║
║  Por encima de 500h, >67% de muestras son CRÍTICAS.              ║
║                                                                  ║
║  SIGUIENTES PASOS (Fase 3):                                      ║
║  → Envolver modelos en API REST (FastAPI)                        ║
║  → Construir base de datos PostgreSQL                            ║
║  → Desarrollar dashboard frontend (React/Streamlit)              ║
║  → Implementar ingesta automática de nuevas muestras             ║
╚══════════════════════════════════════════════════════════════════╝
""")

# Guardar resumen en Excel
with pd.ExcelWriter('outputs_fase2/resumen_fase2_794AC.xlsx', engine='openpyxl') as writer:
    reg_df.to_excel(writer, sheet_name='Resultados_Regresion', index=False)
    per_equipo_df.to_excel(writer, sheet_name='Accuracy_por_Equipo', index=False)
    shap_ranking.to_excel(writer, sheet_name='SHAP_Ranking', index=False)
    if len(df_surv_feat) > 0:
        pd.DataFrame([{
            'MAE_horas': mae_surv, 'RMSE_horas': rmse_surv, 'R2': r2_surv
        }]).to_excel(writer, sheet_name='Supervivencia', index=False)

print("✓ Resumen exportado: outputs_fase2/resumen_fase2_794AC.xlsx")
```

---

## NOTAS FINALES PARA CURSOR

1. **Corregir data leakage del rolling_mean**: asegurarse que `shift(1)` esté siempre
   antes de cualquier rolling. La función `build_features` ya lo hace correctamente.

2. **Manejo de cambios de aceite**: cuando `Hora_Producto` de t es MENOR que el de t-1,
   significa que hubo un cambio de aceite. En ese caso, los lags NO deben cruzar ese
   límite. Agregar lógica en `build_features`:
   ```python
   if es_cambio_aceite[i]:
       # Resetear todos los lags a NaN para esa fila
   ```

3. **Imbalance de clases**: NORMAL es solo el 12.8%. Para el clasificador, usar siempre
   `class_weight='balanced'` en LightGBM y ajustar `scale_pos_weight` en XGBoost.

4. **Optuna n_trials**: con N_TRIALS=50 el entrenamiento toma ~10-20 min. Subir a 100
   para mejor optimización en producción.

5. **Guardar feat_cols**: exportar la lista de features como JSON para garantizar que
   la función de predicción en producción use las mismas columnas:
   ```python
   import json
   with open('models/feat_cols.json', 'w') as f:
       json.dump(feat_cols, f)
   ```

6. **Outputs esperados** en `outputs_fase2/`:
   - `01_confusion_matrix_clasificacion.png`
   - `02_resultados_regresion_t1.xlsx`
   - `03_shap_clasificador.png`
   - `04_shap_por_clase.png`
   - `05_shap_ranking.xlsx`
   - `06_horas_restantes_distribucion.png`
   - `07_supervivencia_pred_vs_real.png`
   - `08_accuracy_por_equipo.png`
   - `09_simulacion_HT012.png` / `09_simulacion_HT001.png`
   - `resumen_fase2_794AC.xlsx`

7. **Outputs esperados** en `models/`:
   - `clasificador_estado_lightgbm.pkl` (o xgboost)
   - `regresor_{variable}.pkl` (uno por cada variable en VARS_LAG)
   - `estimador_horas_hasta_critico.pkl`
   - `feat_cols.json`
