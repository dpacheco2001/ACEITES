# GUÍA MAESTRA DE DESARROLLO — OilMine Analytics
## SaaS Predictivo de Mantenimiento — Flota 794AC Quellaveco
### Documento completo para Claude Opus — Desarrollo de la APP

> **Para Opus:** Esta guía es tu fuente de verdad. La arquitectura hexagonal
> es referencial — tienes autonomía para optimizar estructura, patrones y
> decisiones técnicas durante el desarrollo. Lo que NO es negociable son
> las reglas de ML (sección 4) y la lógica de semáforo (sección 5), porque
> están validadas con datos reales de la mina.
>
> **Lee la Sección 0 primero.** Contiene el mapa exacto de todos los archivos
> existentes en el disco antes de que escribas una sola línea de código.

---

## SECCIÓN 0 — MAPA REAL DE ARCHIVOS

Raíz del proyecto: `C:\Users\lbrya\OneDrive\Escritorio\ACEITES_MINERIA\`

### 0.1 — Archivos que suman al proyecto (los únicos que importan)

```
ACEITES_MINERIA\
│
│  ── Datos ─────────────────────────────────────────────────────────
│
├── DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx
│       ↳ BASE DE DATOS PRINCIPAL. Hoja activa: "794AC QUELLA"
│         3,719 filas × 58 columnas. 33 camiones (HT001–HT053).
│         Feb 2020 – Mar 2024.
│
│  ── Modelos ML (YA ENTRENADOS — solo cargar, nunca re-entrenar) ──
│
├── 📁 models\
│   ├── clasificador_estado_xgboost.pkl
│   │       ↳ Modelo A. XGBoost. Clasifica NORMAL/PRECAUCION/CRITICO.
│   │         Accuracy: 78.65%. Input: vector de 173 features.
│   │
│   ├── estimador_horas_hasta_critico.pkl
│   │       ↳ Modelo C. LightGBM. Estima horas hasta estado crítico.
│   │         MAE: 46.9h. Confiable en rango 20-100h.
│   │
│   ├── feat_cols.json
│   │       ↳ Lista exacta de los 173 nombres de features del entrenamiento.
│   │         CRÍTICO: el vector de inferencia debe respetar este orden.
│   │
│   ├── regresor_TBN_(mg_KOH_g).pkl              R² = 0.140
│   ├── regresor_Viscosidad_a_100_degC_cSt.pkl    R² confiable
│   ├── regresor_Hollin_ABS_01_mm.pkl             R² = 0.632 (mejor regresor)
│   ├── regresor_Fierro_ppm.pkl                   R² confiable
│   ├── regresor_Cobre_ppm.pkl                    R² confiable
│   ├── regresor_Silicio_ppm.pkl                  R² confiable
│   ├── regresor_Oxidación_ABS_01_mm.pkl          R² confiable
│   ├── regresor_Sulfatación_ABS_01_mm.pkl        R² confiable
│   ├── regresor_Nitración_ABS_01_mm.pkl          R² confiable
│   ├── regresor_Aluminio_ppm.pkl                 R² confiable
│   ├── regresor_Potasio_ppm.pkl                  ⚠ R² = -1.59 (baja confianza)
│   └── regresor_Cromo_ppm.pkl                    ⚠ R² = -0.11 (baja confianza)
│           ↳ Modelo B. 12 regresores LightGBM, uno por variable analítica.
│             Predicen el valor de la próxima muestra (t+1).
│
│  ── Notebooks de referencia técnica ────────────────────────────────
│
├── fase2_motor_predictivo_794AC.ipynb
│       ↳ LEER PRIMERO. Contiene el código real de entrenamiento de los
│         3 modelos. Incluye la función predict_next_sample(), la lógica
│         de features con shift(1), el split temporal 80/20, SHAP analysis.
│
├── exploracion_ciclo_vida_794AC.ipynb
│       ↳ LEER SEGUNDO si hay dudas sobre los datos. Explica por qué
│         Hora_Producto es el eje X (no la fecha), el breakpoint crítico
│         a 400-450h, y la irregularidad del muestreo (cada 80-120h).
│
│  ── Contexto del proyecto ──────────────────────────────────────────
│
├── INFORME_DETALLADO_HOJAS_794AC.md
│       ↳ Informe con análisis de cada hoja del Excel. Útil para entender
│         la estructura completa del archivo de datos.
│
└── 📁 Proyecto Aceites SaaS\                        ← Carpeta Cowork activa
    │
    │  ── Usar (fuente de verdad) ───────────────────
    ├── GUIA_ORGANIZACION_Y_PROMPTS.md              ← Este archivo
    ├── PROMPT_CURSOR_fase2_modelo_predictivo.md
    │       ↳ Prompt técnico del entrenamiento. Contiene la lógica
    │         del semáforo, feature engineering completo y parámetros
    │         de Optuna/LightGBM. Leer si el notebook no es suficiente.
    │
    │  ── Archivos legacy — IGNORAR COMPLETAMENTE ───
    ├── PROMPT_CURSOR_fase3_backend_fastapi.md
    │       ↳ OBSOLETO. Prompt viejo de Cursor para Streamlit.
    │         Supersedido por esta guía. No usar.
    ├── PROMPT_CURSOR_fase3_frontend_streamlit.md
    │       ↳ OBSOLETO. Prompt viejo de Cursor para Streamlit.
    │         Supersedido por esta guía. No usar.
    ├── PROMPT_CURSOR_notebook_exploracion_794AC.md
    │       ↳ OBSOLETO. Redundante con exploracion_ciclo_vida_794AC.ipynb.
    └── PROMPT_CURSOR_wavelet_vs_standard_comparison.md
            ↳ OBSOLETO. Wavelet fuera del MVP. No usar.
```

### 0.2 — Archivos que NO aportan al desarrollo (ignorar)

```
En ACEITES_MINERIA\ (raíz):
  analisis_clasificacion_794AC.ipynb     → Clustering inicial, superado por Fase 2
  analisis_clasificacion_794AC.py        → Duplicado del notebook anterior
  fase2b_wavelet_comparison_794AC.ipynb  → Wavelet no entra en el MVP
  INFORME_DETALLADO_HOJAS_794AC.docx     → Duplicado del .md
  OilMine_Analytics_Impacto_Luis_Loayza.pdf/pptx → Pitch comercial, no técnico
  Carlos Parra.pdf                       → No relevante para el desarrollo
  desktop.ini                            → Archivo de sistema Windows
  outputs/                               → Gráficos históricos, no necesarios

En Proyecto Aceites SaaS\ (Cowork):
  PROMPT_CURSOR_fase3_backend_fastapi.md       → Obsoleto (era para Streamlit+Cursor)
  PROMPT_CURSOR_fase3_frontend_streamlit.md    → Obsoleto (era para Streamlit+Cursor)
  PROMPT_CURSOR_notebook_exploracion_794AC.md  → Redundante con el .ipynb
  PROMPT_CURSOR_wavelet_vs_standard_comparison.md → Fuera del MVP
```

### 0.3 — Estructura objetivo (lo que Opus construirá)

El código nuevo irá en carpetas nuevas. **Nada de lo existente se mueve ni modifica.**

```
ACEITES_MINERIA\
│
├── [todo lo de arriba — intacto]
│
├── 📁 src\              ← Opus crea: backend Python con arquitectura hexagonal
│   ├── domain\
│   ├── application\
│   ├── infrastructure\
│   └── interfaces\api\
│
├── 📁 frontend\         ← Opus crea: React + Vite (puerto 5173)
│
├── run_api.py           ← Opus crea: inicia FastAPI en puerto 8000
└── requirements.txt     ← Opus crea: dependencias Python
```

### 0.4 — Paths exactos para el código

```python
# settings.py — paths relativos a ACEITES_MINERIA\ (raíz del proyecto)

EXCEL_PATH      = "DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx"
EXCEL_SHEET     = "794AC QUELLA"
MODELS_DIR      = "models"
CLASIFICADOR    = "models/clasificador_estado_xgboost.pkl"
ESTIMADOR       = "models/estimador_horas_hasta_critico.pkl"
FEAT_COLS_PATH  = "models/feat_cols.json"

# Nombre de archivo de regresor por variable (nombre exacto de columna en Excel):
# f"models/regresor_{nombre_columna}.pkl"
# Ejemplo: "models/regresor_TBN_(mg_KOH_g).pkl"
#          "models/regresor_Hollin_ABS_01_mm.pkl"
```

---

## SECCIÓN 1 — CONTEXTO DE NEGOCIO

### ¿Qué es este sistema?

OilMine Analytics es un sistema de mantenimiento predictivo para la flota de
camiones de acarreo Caterpillar 794AC de la mina Quellaveco (Perú, operada
por Anglo American). El sistema analiza muestras de aceite del motor para:

1. **Clasificar el estado actual** del camión: NORMAL / PRECAUCION / CRITICO
2. **Predecir los valores de la próxima muestra** (t+1) de cada variable analítica
3. **Estimar cuántas horas quedan** antes de que el camión llegue a estado crítico
4. **Generar un semáforo visual** VERDE / AMARILLO / ROJO por equipo

### La flota

- **33 camiones** Caterpillar 794AC activos, identificados como HT001 a HT053
  (hay gaps en la numeración: HT006, HT007... no todos los números existen)
- Datos históricos: febrero 2020 a marzo 2024 (3,719 registros en total)
- Cada camión tiene entre 80 y 180 muestras históricas

### El problema de mantenimiento

Los camiones operan en ciclos. Cada ciclo comienza cuando se cambia el aceite
del motor (Hora_Producto = 0) y termina cuando el aceite se drena o el motor
falla. El aceite se degrada progresivamente. La variable clave es **Hora_Producto**
(horas acumuladas del aceite en el motor), que es el eje temporal real del
análisis — no la fecha del calendario.

**Breakpoint crítico confirmado: 400-450 horas de producto.**
Más allá de ese punto, la probabilidad de estado CRITICO sube drásticamente.

---

## SECCIÓN 2 — DATOS: ESTRUCTURA DEL EXCEL

### Archivo principal

```
DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx
Ubicación: raíz de ACEITES_MINERIA\ (NO está en subcarpeta data/)
Hoja principal: "794AC QUELLA"
```

### Columnas relevantes de la hoja "794AC QUELLA"

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `Equipo` | str | ID del camión (ej: HT001, HT012) |
| `Fecha_Muestra` | date | Fecha en que se tomó la muestra |
| `Hora_Producto` | float | Horas acumuladas del aceite (eje X principal) |
| `TBN_(mg_KOH_g)` | float | Total Base Number — indicador de vida útil del aceite |
| `Viscosidad_a_100_degC_cSt` | float | Viscosidad cinemática a 100°C |
| `Hollin_ABS_01_mm` | float | Nivel de hollín (carbono) en el aceite |
| `Fierro_ppm` | float | Concentración de hierro (desgaste metálico) |
| `Cobre_ppm` | float | Concentración de cobre |
| `Silicio_ppm` | float | Concentración de silicio (contaminación por polvo) |
| `Oxidación_ABS_01_mm` | float | Nivel de oxidación del aceite |
| `Sulfatación_ABS_01_mm` | float | Nivel de sulfatación |
| `Nitración_ABS_01_mm` | float | Nivel de nitración |
| `Potasio_ppm` | float | Concentración de potasio |
| `Aluminio_ppm` | float | Concentración de aluminio |
| `Cromo_ppm` | float | Concentración de cromo |
| `Estado` | str | Etiqueta de estado: NORMAL / PRECAUCION / CRITICO |

### Distribución de estados (desbalance de clases)

```
CRITICO    →  ~55% de los registros
PRECAUCION →  ~32% de los registros
NORMAL     →  ~13% de los registros   ← clase minoritaria
```

> Este desbalance fue tratado con class_weight='balanced' en los modelos.
> El sistema debe mostrar alertas aunque CRITICO sea el estado más común
> porque representa degradación real del aceite.

### Nombres internos de las 12 variables analíticas

Estos son los nombres EXACTOS de columnas en el Excel y en los modelos:

```python
VARIABLES_ANALITICAS = [
    "TBN_(mg_KOH_g)",
    "Viscosidad_a_100_degC_cSt",
    "Hollin_ABS_01_mm",
    "Fierro_ppm",
    "Cobre_ppm",
    "Silicio_ppm",
    "Oxidación_ABS_01_mm",
    "Sulfatación_ABS_01_mm",
    "Nitración_ABS_01_mm",
    "Potasio_ppm",
    "Aluminio_ppm",
    "Cromo_ppm"
]
```

### Nombres de archivos .pkl de regresores (exactos)

```
regresor_TBN_(mg_KOH_g).pkl
regresor_Viscosidad_a_100_degC_cSt.pkl
regresor_Hollin_ABS_01_mm.pkl
regresor_Fierro_ppm.pkl
regresor_Cobre_ppm.pkl
regresor_Silicio_ppm.pkl
regresor_Oxidación_ABS_01_mm.pkl
regresor_Sulfatación_ABS_01_mm.pkl
regresor_Nitración_ABS_01_mm.pkl
regresor_Potasio_ppm.pkl
regresor_Aluminio_ppm.pkl
regresor_Cromo_ppm.pkl
```

---

## SECCIÓN 3 — MODELOS ML (YA ENTRENADOS)

Todos los modelos están en `models/` como archivos `.pkl` listos para cargar.
**No se re-entrenan en la app.** Solo se cargan y se usan para inferencia.

### Modelo A — Clasificador de estado

```
Archivo:   models/clasificador_estado_xgboost.pkl
Tipo:      XGBoost Classifier
Input:     vector de 173 features (ver Sección 4)
Output:    string: "NORMAL" | "PRECAUCION" | "CRITICO"
Accuracy:  78.65% (validación temporal sin data leakage)
```

### Modelo B — Regresores de variables (12 modelos)

```
Archivos:  models/regresor_<VARIABLE>.pkl  (uno por cada variable analítica)
Tipo:      LightGBM Regressor
Input:     vector de 173 features (mismo vector que Modelo A)
Output:    float — valor predicho de esa variable en la próxima muestra (t+1)
```

> Nota: Potasio (R²=-1.59) y Cromo (R²=-0.11) son poco confiables.
> Mostrar sus predicciones con una advertencia visual o flag de baja confianza.

### Modelo C — Estimador de horas hasta estado crítico

```
Archivo:   models/estimador_horas_hasta_critico.pkl
Tipo:      LightGBM Regressor
Input:     vector de 173 features
Output:    float — horas estimadas que quedan antes de llegar a estado CRITICO
MAE:       46.9 horas
R²:        0.20  (distribución muy sesgada, confiable en rango 20-100h)
```

### Lista de features

```
Archivo:   models/feat_cols.json
Contenido: lista de 173 strings con los nombres exactos de las columnas
           que deben alimentar los tres modelos
```

---

## SECCIÓN 4 — INGENIERÍA DE FEATURES (CRÍTICO — LEER COMPLETO)

Esta sección describe cómo construir el vector de 173 features a partir del
historial de un equipo. **La lógica debe ser idéntica a la del entrenamiento.**
Un error aquí produce predicciones incorrectas.

### Parámetros

```python
N_LAGS = 5          # número de valores pasados por variable
ROLLING_WINDOWS = [3, 5]  # ventanas para estadísticas rolling
```

### Proceso para cada variable analítica (aplicar a las 12)

Para una variable `v` y su serie histórica `s` (ordenada por Hora_Producto):

```python
# 1. LAGS — valores pasados
# lag_1 = muestra anterior, lag_2 = dos muestras atrás, etc.
for i in range(1, N_LAGS + 1):
    features[f"{v}_lag_{i}"] = s.shift(i).iloc[-1]

# 2. DELTAS — diferencia entre lags consecutivos
for i in range(1, N_LAGS):
    features[f"{v}_delta_{i}"] = (s.shift(i) - s.shift(i+1)).iloc[-1]

# 3. ROLLING MEAN — media móvil (SIEMPRE con shift(1) primero)
for w in ROLLING_WINDOWS:
    features[f"{v}_rolling_mean_{w}"] = s.shift(1).rolling(w).mean().iloc[-1]

# 4. ROLLING STD — desviación estándar móvil
for w in ROLLING_WINDOWS:
    features[f"{v}_rolling_std_{w}"] = s.shift(1).rolling(w).std().iloc[-1]

# 5. TREND SLOPE — pendiente de regresión lineal sobre los últimos 5 puntos
# Usar solo los N_LAGS valores más recientes (excluyendo el actual)
recent = s.shift(1).iloc[-N_LAGS:]
if len(recent.dropna()) >= 2:
    x = np.arange(len(recent))
    slope = np.polyfit(x[~np.isnan(recent)], recent.dropna(), 1)[0]
    features[f"{v}_trend_slope"] = slope
```

### Features adicionales (no de variables analíticas)

```python
# Horas actuales del producto (la variable más importante, SHAP=0.961)
features["horas_actuales"] = hora_producto_actual

# Estado anterior codificado numéricamente
estado_map = {"NORMAL": 0, "PRECAUCION": 1, "CRITICO": 2}
features["estado_lag1"] = estado_map.get(estado_anterior, 2)
```

### Regla anti-leakage (NUNCA violar)

```
❌ INCORRECTO: rolling_mean calculado sobre s (incluye t actual)
✅ CORRECTO:   rolling_mean calculado sobre s.shift(1) (excluye t actual)

Si se viola esta regla, los modelos predicen con datos futuros
y los resultados son artificialmente perfectos (R²=1.0 en entrenamiento,
desastrosos en producción).
```

### Cómo construir el vector final

```python
import json
import numpy as np

# Cargar lista exacta de features del entrenamiento
with open("models/feat_cols.json", "r") as f:
    feat_cols = json.load(f)  # lista de 173 strings

# Construir dict de features con el proceso de arriba
feature_dict = build_features(historial_equipo)

# Alinear con feat_cols (agregar 0.0 si falta alguna feature)
vector = np.array([feature_dict.get(col, 0.0) for col in feat_cols])
# shape: (173,) — listo para pasar a model.predict([vector])
```

---

## SECCIÓN 5 — LÓGICA DEL SEMÁFORO

El semáforo combina tres señales para dar el estado final del equipo.
Esta lógica está validada con datos reales — no cambiarla sin análisis.

```python
def calcular_semaforo(
    estado_modelo: str,        # "NORMAL" | "PRECAUCION" | "CRITICO"
    horas_actuales: float,     # Hora_Producto de la última muestra
    horas_hasta_critico: float # Output del Modelo C
) -> str:                      # "VERDE" | "AMARILLO" | "ROJO"

    # ROJO: cualquiera de estas condiciones
    if estado_modelo == "CRITICO":
        return "ROJO"
    if horas_actuales >= 400:
        return "ROJO"
    if horas_hasta_critico is not None and horas_hasta_critico <= 50:
        return "ROJO"

    # AMARILLO: zona de precaución
    if estado_modelo == "PRECAUCION":
        return "AMARILLO"
    if horas_actuales >= 300:
        return "AMARILLO"
    if horas_hasta_critico is not None and horas_hasta_critico <= 150:
        return "AMARILLO"

    # VERDE: todo en orden
    return "VERDE"
```

### Significado operacional para el ingeniero

| Semáforo | Acción recomendada |
|----------|-------------------|
| 🟢 VERDE | Operación normal. Próxima muestra en ciclo regular. |
| 🟡 AMARILLO | Monitoreo aumentado. Programar revisión preventiva pronto. |
| 🔴 ROJO | Detener para inspección. Considerar cambio de aceite inmediato. |

---

## SECCIÓN 6 — API REST: ENDPOINTS REQUERIDOS

### Base URL: `http://localhost:8000`

---

**GET `/health`**
Verificar que el backend está activo.

Response:
```json
{ "status": "ok", "modelos_cargados": true }
```

---

**GET `/equipos`**
Listar todos los equipos disponibles.

Response:
```json
{
  "equipos": ["HT001", "HT002", "HT003", "..."]
}
```

---

**GET `/flota/resumen`**
Estado actual de toda la flota. Es el endpoint principal del dashboard.

Response:
```json
{
  "total_equipos": 33,
  "criticos": 5,
  "precaucion": 12,
  "normales": 16,
  "equipos": [
    {
      "equipo": "HT001",
      "semaforo": "ROJO",
      "estado_modelo": "CRITICO",
      "horas_actuales": 445.0,
      "horas_hasta_critico": 12.5,
      "ultima_muestra_fecha": "2024-03-15",
      "total_muestras": 143
    }
  ]
}
```

---

**GET `/equipos/{equipo_id}/prediccion`**
Predicción completa para un equipo específico.

Response:
```json
{
  "equipo": "HT012",
  "semaforo": "AMARILLO",
  "estado_modelo": "PRECAUCION",
  "horas_actuales": 312.0,
  "horas_hasta_critico": 88.5,
  "predicciones_t1": {
    "TBN_(mg_KOH_g)": 6.2,
    "Viscosidad_a_100_degC_cSt": 15.1,
    "Hollin_ABS_01_mm": 28.4,
    "Fierro_ppm": 45.2,
    "Cobre_ppm": 12.1,
    "Silicio_ppm": 8.3,
    "Oxidación_ABS_01_mm": 11.2,
    "Sulfatación_ABS_01_mm": 9.8,
    "Nitración_ABS_01_mm": 7.5,
    "Potasio_ppm": 1.1,
    "Aluminio_ppm": 3.2,
    "Cromo_ppm": 0.8
  },
  "variables_baja_confianza": ["Potasio_ppm", "Cromo_ppm"],
  "ultima_muestra_fecha": "2024-02-20"
}
```

---

**GET `/equipos/{equipo_id}/historial`**
Historial completo de muestras de un equipo, ordenado por Hora_Producto.

Response:
```json
{
  "equipo": "HT012",
  "total_muestras": 156,
  "historial": [
    {
      "fecha": "2023-01-10",
      "hora_producto": 87.5,
      "estado": "NORMAL",
      "TBN_(mg_KOH_g)": 9.1,
      "Viscosidad_a_100_degC_cSt": 14.8,
      "Hollin_ABS_01_mm": 12.3,
      "Fierro_ppm": 21.0,
      "Cobre_ppm": 8.5,
      "Silicio_ppm": 5.2,
      "Oxidación_ABS_01_mm": 6.1,
      "Sulfatación_ABS_01_mm": 5.3,
      "Nitración_ABS_01_mm": 4.2,
      "Potasio_ppm": 0.9,
      "Aluminio_ppm": 1.8,
      "Cromo_ppm": 0.4
    }
  ]
}
```

---

**POST `/equipos/{equipo_id}/muestras`**
Registrar una nueva muestra en el Excel y recibir predicción inmediata.

Request body:
```json
{
  "fecha": "2024-04-20",
  "hora_producto": 380.0,
  "TBN_(mg_KOH_g)": 5.8,
  "Viscosidad_a_100_degC_cSt": 15.4,
  "Hollin_ABS_01_mm": 35.2,
  "Fierro_ppm": 68.1,
  "Cobre_ppm": 18.3,
  "Silicio_ppm": 12.7,
  "Oxidación_ABS_01_mm": 14.5,
  "Sulfatación_ABS_01_mm": 11.2,
  "Nitración_ABS_01_mm": 9.8,
  "Potasio_ppm": 1.5,
  "Aluminio_ppm": 4.1,
  "Cromo_ppm": 0.9
}
```

Response: mismo formato que `/equipos/{equipo_id}/prediccion`

---

**GET `/equipos/{equipo_id}/exportar`**
Descargar el historial de un equipo como archivo Excel o CSV.

Query params: `?formato=excel` o `?formato=csv`
Response: archivo binario descargable

---

## SECCIÓN 7 — FRONTEND: PANTALLAS REQUERIDAS

Stack: **React + Vite** corriendo en `localhost:5173`.
CORS habilitado en el backend para `http://localhost:5173`.

### Pantalla 1 — Dashboard de Flota (`/`)

Objetivo: vista de un vistazo del estado de todos los camiones.

Elementos requeridos:
- Header con el nombre "OilMine Analytics" y logo/ícono de camión
- KPIs en tarjetas: total equipos, cantidad ROJO, AMARILLO, VERDE
- Grid de tarjetas de equipos (una por camión), cada tarjeta muestra:
  - ID del equipo (ej: HT012)
  - Círculo de semáforo con color (rojo/amarillo/verde)
  - Estado del modelo (CRITICO / PRECAUCION / NORMAL)
  - Horas actuales de producto
  - Horas estimadas hasta crítico
- Filtro por semáforo (mostrar solo ROJO, solo AMARILLO, todos)
- Ordenar por semáforo (ROJO primero)

### Pantalla 2 — Detalle de Equipo (`/equipo/:id`)

Objetivo: análisis profundo de un camión individual.

Elementos requeridos:
- Semáforo grande con estado actual
- KPIs: horas actuales, horas hasta crítico, total muestras, fecha última muestra
- Gráfico de degradación temporal: eje X = Hora_Producto, eje Y = valor de la variable.
  Mostrar curva histórica con puntos coloreados por estado (verde/amarillo/rojo).
  Agregar un marcador estrella (★) en el valor predicho t+1.
  Permitir seleccionar cuál variable graficar (dropdown).
- Gauges/velocímetros: uno por cada variable analítica mostrando el valor actual
  vs. los límites de alerta. Las variables con baja confianza llevan un ícono ⚠️.
- Tabla de historial completo con todas las muestras (paginada, ordenada por fecha desc)
- Botón "Registrar nueva muestra" → navega a Pantalla 3

### Pantalla 3 — Nueva Muestra (`/nueva-muestra/:id`)

Objetivo: ingresar una nueva muestra y ver la predicción resultante.

Elementos requeridos:
- Formulario con campos para:
  - Fecha de la muestra (date picker)
  - Hora_Producto (número con decimales)
  - Las 12 variables analíticas (inputs numéricos)
- Validaciones: ningún campo vacío, hora_producto > 0, valores > 0
- Al enviar: POST a `/equipos/{id}/muestras`
- Resultado: mostrar el semáforo resultante y los valores predichos de t+1
  con una animación o transición visual clara

### Pantalla 4 — Reportes (`/reportes`)

Objetivo: exportar datos para análisis externo.

Elementos requeridos:
- Selector de equipo (dropdown con todos los IDs)
- Selector de rango de fechas
- Botón "Descargar Excel" → llama a `/equipos/{id}/exportar?formato=excel`
- Botón "Descargar CSV" → llama a `/equipos/{id}/exportar?formato=csv`
- Opción de exportar resumen de toda la flota

---

## SECCIÓN 8 — LÍMITES DE ALERTA POR VARIABLE

Estos valores determinan las zonas de color en los gauges del frontend.
Basados en estándares de mantenimiento de Caterpillar 794AC.

| Variable | Normal (Verde) | Precaución (Amarillo) | Crítico (Rojo) |
|----------|---------------|----------------------|----------------|
| TBN_(mg_KOH_g) | > 7.0 | 5.0 – 7.0 | < 5.0 |
| Viscosidad_a_100_degC_cSt | 13.0 – 17.0 | 11.0–13.0 o 17.0–19.0 | < 11.0 o > 19.0 |
| Hollin_ABS_01_mm | < 20 | 20 – 35 | > 35 |
| Fierro_ppm | < 40 | 40 – 80 | > 80 |
| Cobre_ppm | < 15 | 15 – 30 | > 30 |
| Silicio_ppm | < 15 | 15 – 25 | > 25 |
| Oxidación_ABS_01_mm | < 15 | 15 – 25 | > 25 |
| Sulfatación_ABS_01_mm | < 15 | 15 – 25 | > 25 |
| Nitración_ABS_01_mm | < 15 | 15 – 25 | > 25 |
| Potasio_ppm | < 5 | 5 – 10 | > 10 |
| Aluminio_ppm | < 10 | 10 – 20 | > 20 |
| Cromo_ppm | < 5 | 5 – 10 | > 10 |

---

## SECCIÓN 9 — ARQUITECTURA REFERENCIAL

Esta es la propuesta de partida. **Opus decide la estructura final.**

### Stack

```
Backend   →  Python 3.10+ + FastAPI + Uvicorn   (puerto 8000)
Frontend  →  React 18 + Vite + Tailwind CSS     (puerto 5173)
BD (MVP)  →  Excel + openpyxl + threading.Lock
ML        →  joblib/pickle para cargar .pkl
```

### Estructura de capas (Hexagonal / Ports & Adapters)

```
src/
├── domain/              ← Entidades y lógica pura de negocio
│   ├── entities/        ← Equipo, Muestra, Prediccion
│   ├── value_objects/   ← EstadoEquipo (enum), Semaforo (enum)
│   └── services/        ← SemaforoService (lógica de la Sección 5)
│
├── application/         ← Casos de uso + puertos (interfaces ABC)
│   ├── ports/
│   │   ├── i_equipo_repository.py     ← ABC: obtener_historial, listar_equipos
│   │   ├── i_muestra_repository.py    ← ABC: registrar_muestra
│   │   ├── i_predictor.py             ← ABC: predecir(historial) → Prediccion
│   │   └── i_feature_builder.py       ← ABC: construir_vector(historial) → np.array
│   └── use_cases/
│       ├── predecir_equipo.py
│       ├── registrar_muestra.py
│       ├── obtener_resumen_flota.py
│       └── obtener_historial.py
│
├── infrastructure/      ← Implementaciones concretas
│   ├── persistence/excel/
│   │   ├── excel_manager.py           ← threading.Lock, cargar/guardar Excel
│   │   ├── excel_equipo_repository.py ← implementa IEquipoRepository
│   │   └── excel_muestra_repository.py← implementa IMuestraRepository
│   ├── ml/
│   │   ├── modelo_loader.py           ← Singleton, carga todos los .pkl al inicio
│   │   ├── feature_builder.py         ← implementa IFeatureBuilder (Sección 4)
│   │   └── predictor_adapter.py       ← implementa IPredictor (usa los 3 modelos)
│   └── config/
│       └── settings.py                ← rutas, puertos, parámetros
│
└── interfaces/
    └── api/             ← FastAPI
        ├── main.py      ← App + CORS + startup (cargar modelos)
        ├── dependencies.py ← inyección de dependencias
        ├── routers/
        │   ├── health.py
        │   ├── flota.py
        │   ├── equipos.py
        │   └── muestras.py
        └── schemas/
            ├── requests.py
            └── responses.py

frontend/                ← React + Vite (separado del src Python)
├── src/
│   ├── components/      ← Semaforo, GaugeChart, DegradacionChart, TablaHistorial
│   ├── pages/           ← Flota, Equipo, NuevaMuestra, Reportes
│   ├── services/        ← api.js (fetch wrapper hacia localhost:8000)
│   └── store/           ← estado global ligero (Zustand o Context)
├── package.json
└── vite.config.js       ← proxy /api → localhost:8000 para evitar CORS en dev

run_api.py               ← uvicorn src.interfaces.api.main:app --port 8000
requirements.txt
```

### Regla de dependencias (no negociable en hexagonal)

```
domain         ← no importa nada del proyecto
application    ← solo importa domain
infrastructure ← importa application (implementa sus puertos)
interfaces/api ← importa application + infrastructure
```

---

## SECCIÓN 10 — INSTRUCCIONES DE ARRANQUE

### Backend

```bash
cd ACEITES_MINERIA
pip install fastapi uvicorn openpyxl lightgbm xgboost pandas numpy joblib
python run_api.py
# Verificar: http://localhost:8000/docs
```

### Frontend

```bash
cd ACEITES_MINERIA/frontend
npm install
npm run dev
# Abrir: http://localhost:5173
```

### Verificación rápida del sistema

```bash
# Probar que los modelos cargan correctamente
curl http://localhost:8000/health

# Probar que hay equipos disponibles
curl http://localhost:8000/equipos

# Probar predicción para HT001
curl http://localhost:8000/equipos/HT001/prediccion
```

---

## SECCIÓN 11 — RESTRICCIONES Y DECISIONES TÉCNICAS DEL MVP

```
✅ Despliegue 100% local (sin Docker, sin cloud)
✅ Excel como base de datos (sin PostgreSQL)
✅ Sin autenticación de usuarios
✅ React + Vite como frontend (sin Streamlit)
✅ Modelos ML ya entrenados (sin re-entrenamiento en la app)

❌ No usar MAPE como métrica para Potasio, Cromo, Oxidación
   (valores cercanos a 0 producen MAPE = millones%)
   → Usar MAE como métrica principal para esas variables

❌ No mostrar predicciones de Potasio y Cromo sin advertencia
   (R² negativo → baja confianza)

❌ No ordenar por fecha calendario, siempre por Hora_Producto
   (el muestreo es irregular, la fecha no refleja degradación)
```

---

## SECCIÓN 12 — ROADMAP POST-MVP

| Versión | Funcionalidad | Tecnología |
|---------|--------------|------------|
| v1.5 | Migración de Excel a base de datos relacional | PostgreSQL + SQLAlchemy + Alembic |
| v2.0 | Autenticación multi-usuario (ingenieros vs admin) | JWT + bcrypt |
| v2.5 | Frontend de producción optimizado | React + optimizaciones de bundle |
| v3.0 | Integración Wavelet-Interp para regresor TBN | PyWavelets en feature_builder |
| v3.5 | Deploy en nube | Railway / AWS EC2 / Azure |
| v4.0 | Alertas automáticas por email/SMS | SendGrid / Twilio |
