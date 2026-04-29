import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.cluster import KMeans
from xgboost import XGBClassifier
import shap
import warnings
import os
warnings.filterwarnings('ignore')

plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11

OUTPUT_DIR = r'c:\Users\lbrya\OneDrive\Escritorio\ACEITES_MINERIA\resultados_analisis'
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_PATH = r'c:\Users\lbrya\OneDrive\Escritorio\ACEITES_MINERIA\DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx'

# =============================================================================
# 1. CARGA Y EXPLORACIÓN DE DATOS
# =============================================================================
print("=" * 80)
print("1. CARGA Y EXPLORACIÓN DE LA BASE DE DATOS")
print("=" * 80)

df = pd.read_excel(FILE_PATH, sheet_name='794AC QUELLA')

print(f"\nDimensiones del dataset: {df.shape[0]} filas x {df.shape[1]} columnas")
print(f"\nDistribución de la variable ESTADO:")
print(df['Estado'].value_counts())
print(f"\nPorcentaje:")
print((df['Estado'].value_counts() / len(df) * 100).round(2))

# =============================================================================
# 2. LIMPIEZA Y PREPARACIÓN DE DATOS
# =============================================================================
print("\n" + "=" * 80)
print("2. LIMPIEZA Y PREPARACIÓN DE DATOS")
print("=" * 80)

cols_excluir = ['Codigo', 'Fecha', 'Fecha - Año', 'Equipo', 'PRUEBA', 'Producto',
                'Estado', 'Observacion', 'Accion_Sugerida', 'AGUA (CRAQUEO) TRAZ/NEG ']

feature_cols = [c for c in df.columns if c not in cols_excluir]
print(f"\nVariables feature candidatas ({len(feature_cols)}):")
for c in feature_cols:
    print(f"  - {c}")

df_model = df[feature_cols + ['Estado']].copy()

for col in feature_cols:
    if df_model[col].dtype == 'object':
        df_model[col] = pd.to_numeric(df_model[col], errors='coerce')

pct_null = df_model[feature_cols].isnull().sum() / len(df_model) * 100
cols_drop = pct_null[pct_null > 50].index.tolist()
print(f"\nColumnas eliminadas por >50% nulos: {cols_drop}")
feature_cols = [c for c in feature_cols if c not in cols_drop]
df_model = df_model[feature_cols + ['Estado']]

print(f"\nNulos restantes antes de imputación:")
nulls = df_model[feature_cols].isnull().sum()
nulls_nonzero = nulls[nulls > 0]
for col, val in nulls_nonzero.items():
    print(f"  {col}: {val} ({val/len(df_model)*100:.1f}%)")

for col in feature_cols:
    if df_model[col].isnull().sum() > 0:
        df_model[col] = df_model[col].fillna(df_model[col].median())

df_model = df_model.dropna(subset=['Estado'])
print(f"\nDataset final para modelado: {df_model.shape[0]} filas x {len(feature_cols)} features")

# =============================================================================
# 3. ANÁLISIS EXPLORATORIO POR ESTADO
# =============================================================================
print("\n" + "=" * 80)
print("3. ANÁLISIS EXPLORATORIO POR ESTADO")
print("=" * 80)

stats_by_estado = df_model.groupby('Estado')[feature_cols].agg(['mean', 'median', 'std', 'min', 'max'])
stats_by_estado.to_excel(os.path.join(OUTPUT_DIR, 'estadisticas_por_estado.xlsx'))
print("\nEstadísticas por estado guardadas en 'estadisticas_por_estado.xlsx'")

print("\n--- MEDIAS POR ESTADO (variables más relevantes) ---")
means = df_model.groupby('Estado')[feature_cols].mean().T
print(means.to_string())

# Boxplots de las variables más importantes por estado
top_vars = ['TBN (mg KOH/g)', 'Viscosidad a 100 °C cSt', 'Oxidación ABS/01 mm',
            'Nitración ABS/01 mm', 'Sulfatación ABS/01 mm', 'Hollin ABS/01 mm',
            'Fierro ppm', 'Cromo ppm', 'Plomo ppm', 'Cobre ppm', 'Silicio ppm', 'Potasio ppm']
top_vars_exist = [v for v in top_vars if v in feature_cols]

if not top_vars_exist:
    top_vars_exist = feature_cols[:12]

fig, axes = plt.subplots(3, 4, figsize=(20, 15))
axes = axes.flatten()
order = ['NORMAL', 'PRECAUCION', 'CRITICO']
for i, var in enumerate(top_vars_exist[:12]):
    ax = axes[i]
    data_plot = df_model[df_model['Estado'].isin(order)]
    sns.boxplot(data=data_plot, x='Estado', y=var, order=order, ax=ax,
                palette={'NORMAL': '#2ecc71', 'PRECAUCION': '#f39c12', 'CRITICO': '#e74c3c'})
    ax.set_title(var, fontsize=10, fontweight='bold')
    ax.set_xlabel('')
for j in range(len(top_vars_exist), 12):
    axes[j].set_visible(False)
plt.suptitle('Distribución de Variables por Estado - Flota 794AC', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'boxplots_por_estado.png'), dpi=150, bbox_inches='tight')
plt.close()
print("Boxplots guardados en 'boxplots_por_estado.png'")

# =============================================================================
# 4. MODELO DE CLASIFICACIÓN (XGBoost + Random Forest)
# =============================================================================
print("\n" + "=" * 80)
print("4. MODELO DE CLASIFICACIÓN")
print("=" * 80)

X = df_model[feature_cols].values
le = LabelEncoder()
y = le.fit_transform(df_model['Estado'])
class_names = le.classes_
print(f"\nClases codificadas: {dict(zip(range(len(class_names)), class_names))}")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
print(f"Train: {X_train.shape[0]} | Test: {X_test.shape[0]}")

# --- XGBoost ---
print("\n--- XGBoost Classifier ---")
xgb_model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric='mlogloss',
    use_label_encoder=False
)
xgb_model.fit(X_train, y_train)
y_pred_xgb = xgb_model.predict(X_test)
acc_xgb = accuracy_score(y_test, y_pred_xgb)
print(f"Accuracy XGBoost: {acc_xgb:.4f}")
print("\nReporte de Clasificación (XGBoost):")
print(classification_report(y_test, y_pred_xgb, target_names=class_names))

# Cross-validation
cv_scores = cross_val_score(xgb_model, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=42), scoring='accuracy')
print(f"Cross-Validation Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# --- Random Forest ---
print("\n--- Random Forest Classifier ---")
rf_model = RandomForestClassifier(n_estimators=300, max_depth=15, random_state=42, n_jobs=-1)
rf_model.fit(X_train, y_train)
y_pred_rf = rf_model.predict(X_test)
acc_rf = accuracy_score(y_test, y_pred_rf)
print(f"Accuracy Random Forest: {acc_rf:.4f}")
print("\nReporte de Clasificación (Random Forest):")
print(classification_report(y_test, y_pred_rf, target_names=class_names))

# Confusion Matrix
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
for ax, y_pred, title in zip(axes, [y_pred_xgb, y_pred_rf], ['XGBoost', 'Random Forest']):
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=class_names,
                yticklabels=class_names, ax=ax)
    ax.set_title(f'Matriz de Confusión - {title}', fontweight='bold')
    ax.set_ylabel('Real')
    ax.set_xlabel('Predicho')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'matrices_confusion.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\nMatrices de confusión guardadas en 'matrices_confusion.png'")

# =============================================================================
# 5. FEATURE IMPORTANCE (Random Forest)
# =============================================================================
print("\n" + "=" * 80)
print("5. IMPORTANCIA DE VARIABLES (Random Forest)")
print("=" * 80)

importances = pd.DataFrame({
    'Variable': feature_cols,
    'Importancia_RF': rf_model.feature_importances_,
    'Importancia_XGB': xgb_model.feature_importances_
}).sort_values('Importancia_RF', ascending=False)

print("\nTop 20 Variables más importantes (Random Forest):")
print(importances.head(20).to_string(index=False))

fig, axes = plt.subplots(1, 2, figsize=(18, 10))
top20 = importances.head(20)

axes[0].barh(range(20), top20['Importancia_RF'].values, color='#3498db')
axes[0].set_yticks(range(20))
axes[0].set_yticklabels(top20['Variable'].values)
axes[0].invert_yaxis()
axes[0].set_title('Top 20 - Random Forest', fontweight='bold')
axes[0].set_xlabel('Importancia')

top20_xgb = importances.sort_values('Importancia_XGB', ascending=False).head(20)
axes[1].barh(range(20), top20_xgb['Importancia_XGB'].values, color='#e74c3c')
axes[1].set_yticks(range(20))
axes[1].set_yticklabels(top20_xgb['Variable'].values)
axes[1].invert_yaxis()
axes[1].set_title('Top 20 - XGBoost', fontweight='bold')
axes[1].set_xlabel('Importancia')

plt.suptitle('Importancia de Variables para Clasificación de Estado', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'feature_importance.png'), dpi=150, bbox_inches='tight')
plt.close()
print("Gráfico de importancia guardado en 'feature_importance.png'")

# =============================================================================
# 6. ANÁLISIS SHAP
# =============================================================================
print("\n" + "=" * 80)
print("6. ANÁLISIS SHAP - Importancia y Contribución de Variables")
print("=" * 80)

explainer = shap.TreeExplainer(xgb_model)
shap_values_raw = explainer.shap_values(X_test)

if isinstance(shap_values_raw, list):
    shap_values = shap_values_raw
    n_classes = len(shap_values)
else:
    if shap_values_raw.ndim == 3:
        shap_values = [shap_values_raw[:, :, i] for i in range(shap_values_raw.shape[2])]
        n_classes = len(shap_values)
    else:
        shap_values = [shap_values_raw]
        n_classes = 1

print(f"SHAP values: {n_classes} clases, shape por clase: {shap_values[0].shape}")

X_test_df = pd.DataFrame(X_test, columns=feature_cols)

# SHAP Summary Plot (global)
fig, ax = plt.subplots(figsize=(14, 10))
if n_classes > 1:
    shap_abs_all = np.zeros_like(shap_values[0])
    for sv in shap_values:
        shap_abs_all += np.abs(sv)
    shap.summary_plot(shap_abs_all, X_test_df, feature_names=feature_cols,
                      show=False, max_display=20, plot_type='bar')
else:
    shap.summary_plot(shap_values[0], X_test_df, feature_names=feature_cols,
                      show=False, max_display=20)
plt.title('SHAP Summary Plot - Importancia Global', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'shap_summary_global.png'), dpi=150, bbox_inches='tight')
plt.close()
print("SHAP Summary Plot global guardado")

# SHAP por cada clase
for i, clase in enumerate(class_names[:n_classes]):
    fig, ax = plt.subplots(figsize=(14, 10))
    shap.summary_plot(shap_values[i], X_test_df, feature_names=feature_cols,
                      show=False, max_display=20)
    plt.title(f'SHAP Values - Clase: {clase}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f'shap_summary_{clase}.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"SHAP Summary Plot para '{clase}' guardado")

# SHAP mean absolute values per class
print("\n--- Importancia SHAP media absoluta por clase ---")
for i, clase in enumerate(class_names[:n_classes]):
    shap_abs_mean = np.abs(shap_values[i]).mean(axis=0)
    shap_df = pd.DataFrame({
        'Variable': feature_cols,
        'SHAP_mean_abs': shap_abs_mean
    }).sort_values('SHAP_mean_abs', ascending=False)
    print(f"\n  Top 15 variables para '{clase}':")
    print(f"  {'Variable':<35} {'SHAP medio abs':>15}")
    print(f"  {'-'*50}")
    for _, row in shap_df.head(15).iterrows():
        print(f"  {row['Variable']:<35} {row['SHAP_mean_abs']:>15.4f}")

# SHAP Bar plot
fig, ax = plt.subplots(figsize=(14, 8))
shap_global_importance = np.zeros(len(feature_cols))
for i in range(n_classes):
    shap_global_importance += np.abs(shap_values[i]).mean(axis=0)
shap_global_importance /= n_classes

shap_imp_df = pd.DataFrame({
    'Variable': feature_cols,
    'SHAP_Importancia': shap_global_importance
}).sort_values('SHAP_Importancia', ascending=False).head(20)

plt.barh(range(20), shap_imp_df['SHAP_Importancia'].values[::-1], color='#9b59b6')
plt.yticks(range(20), shap_imp_df['Variable'].values[::-1])
plt.title('Top 20 Variables - Importancia SHAP Global (media absoluta)', fontsize=14, fontweight='bold')
plt.xlabel('Mean |SHAP value|')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'shap_bar_global.png'), dpi=150, bbox_inches='tight')
plt.close()
print("\nSHAP Bar plot global guardado")

# =============================================================================
# 7. PARÁMETROS / INTERVALOS DETERMINANTES POR ESTADO
# =============================================================================
print("\n" + "=" * 80)
print("7. PARÁMETROS DETERMINANTES POR ESTADO (Intervalos)")
print("=" * 80)

top_features = shap_imp_df['Variable'].tolist()

print("\n--- Intervalos de las Top 20 variables por Estado ---")
print(f"\n{'Variable':<35} {'Estado':<15} {'Min':>10} {'P25':>10} {'Mediana':>10} {'P75':>10} {'Max':>10} {'Media':>10}")
print("-" * 115)

intervals_data = []
for var in top_features:
    for estado in ['NORMAL', 'PRECAUCION', 'CRITICO']:
        subset = df_model[df_model['Estado'] == estado][var]
        stats = {
            'Variable': var,
            'Estado': estado,
            'Min': subset.min(),
            'P25': subset.quantile(0.25),
            'Mediana': subset.median(),
            'P75': subset.quantile(0.75),
            'Max': subset.max(),
            'Media': subset.mean()
        }
        intervals_data.append(stats)
        print(f"{var:<35} {estado:<15} {stats['Min']:>10.3f} {stats['P25']:>10.3f} {stats['Mediana']:>10.3f} {stats['P75']:>10.3f} {stats['Max']:>10.3f} {stats['Media']:>10.3f}")
    print()

intervals_df = pd.DataFrame(intervals_data)
intervals_df.to_excel(os.path.join(OUTPUT_DIR, 'intervalos_por_estado.xlsx'), index=False)
print("\nIntervalos guardados en 'intervalos_por_estado.xlsx'")

# =============================================================================
# 8. ANÁLISIS DE CLUSTER (K-Means) para validación
# =============================================================================
print("\n" + "=" * 80)
print("8. ANÁLISIS DE CLUSTER (K-Means) - Validación")
print("=" * 80)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_model[feature_cols])

kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
clusters = kmeans.fit_predict(X_scaled)
df_model_cluster = df_model.copy()
df_model_cluster['Cluster'] = clusters

cross_tab = pd.crosstab(df_model_cluster['Estado'], df_model_cluster['Cluster'],
                        margins=True, margins_name='Total')
print("\nTabla cruzada Estado vs Cluster K-Means:")
print(cross_tab)

print("\n% por Estado dentro de cada Cluster:")
cross_pct = pd.crosstab(df_model_cluster['Estado'], df_model_cluster['Cluster'], normalize='columns') * 100
print(cross_pct.round(2))

fig, ax = plt.subplots(figsize=(10, 6))
cross_pct_plot = pd.crosstab(df_model_cluster['Cluster'], df_model_cluster['Estado'], normalize='index') * 100
cross_pct_plot[['NORMAL', 'PRECAUCION', 'CRITICO']].plot(kind='bar', stacked=True, ax=ax,
    color=['#2ecc71', '#f39c12', '#e74c3c'])
plt.title('Composición de Estados por Cluster K-Means', fontsize=14, fontweight='bold')
plt.xlabel('Cluster')
plt.ylabel('Porcentaje (%)')
plt.legend(title='Estado')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, 'clusters_vs_estado.png'), dpi=150, bbox_inches='tight')
plt.close()
print("Gráfico Clusters vs Estado guardado")

# Centroides del cluster en variables originales
centroids_scaled = kmeans.cluster_centers_
centroids_original = scaler.inverse_transform(centroids_scaled)
centroids_df = pd.DataFrame(centroids_original, columns=feature_cols)
centroids_df.index = [f'Cluster_{i}' for i in range(3)]

print("\nCentroides de los clusters (top 15 variables):")
top15_vars = shap_imp_df['Variable'].head(15).tolist()
top15_exist = [v for v in top15_vars if v in feature_cols]
print(centroids_df[top15_exist].T.to_string())

# =============================================================================
# 9. REGLAS DE DECISIÓN SIMPLIFICADAS
# =============================================================================
print("\n" + "=" * 80)
print("9. REGLAS DE CLASIFICACIÓN DERIVADAS DEL ANÁLISIS")
print("=" * 80)

top10 = shap_imp_df['Variable'].head(10).tolist()
print("\nLas 10 variables más determinantes para la clasificación del Estado:")
for i, var in enumerate(top10, 1):
    print(f"\n  {i}. {var}")
    for estado in ['NORMAL', 'PRECAUCION', 'CRITICO']:
        subset = df_model[df_model['Estado'] == estado][var]
        p10 = subset.quantile(0.10)
        p90 = subset.quantile(0.90)
        print(f"     {estado:<15}: Rango típico (P10-P90) = [{p10:.3f} - {p90:.3f}], Mediana = {subset.median():.3f}")

# =============================================================================
# 10. RESUMEN EJECUTIVO
# =============================================================================
print("\n" + "=" * 80)
print("10. RESUMEN EJECUTIVO")
print("=" * 80)

print(f"""
ANÁLISIS DE CLASIFICACIÓN DE ESTADOS - FLOTA 794AC QUELLAVECO
=============================================================

Dataset: {df_model.shape[0]} muestras de aceite con {len(feature_cols)} variables analíticas.

Distribución de Estados:
  - NORMAL:     {(df_model['Estado']=='NORMAL').sum():>5} ({(df_model['Estado']=='NORMAL').sum()/len(df_model)*100:.1f}%)
  - PRECAUCION: {(df_model['Estado']=='PRECAUCION').sum():>5} ({(df_model['Estado']=='PRECAUCION').sum()/len(df_model)*100:.1f}%)
  - CRITICO:    {(df_model['Estado']=='CRITICO').sum():>5} ({(df_model['Estado']=='CRITICO').sum()/len(df_model)*100:.1f}%)

Rendimiento de Modelos:
  - XGBoost:       {acc_xgb:.4f} accuracy
  - Random Forest: {acc_rf:.4f} accuracy
  - Cross-Val (5-fold): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})

Top 10 Variables más influyentes (SHAP):
""")
for i, var in enumerate(top10, 1):
    print(f"  {i:>2}. {var}")

print(f"""
Archivos generados en: {OUTPUT_DIR}
  - estadisticas_por_estado.xlsx
  - intervalos_por_estado.xlsx
  - boxplots_por_estado.png
  - matrices_confusion.png
  - feature_importance.png
  - shap_summary_global.png
  - shap_summary_CRITICO.png
  - shap_summary_NORMAL.png
  - shap_summary_PRECAUCION.png
  - shap_bar_global.png
  - clusters_vs_estado.png
""")

print("=" * 80)
print("ANÁLISIS COMPLETADO EXITOSAMENTE")
print("=" * 80)
