# PROMPT PARA CURSOR — Fase 3: Backend FastAPI
## SaaS Predictivo de Aceites — Flota 794AC Quellaveco
## Base de datos: Excel (MVP — sin PostgreSQL)

---

## CONTEXTO DEL PROYECTO

Este es el backend del **SaaS de mantenimiento predictivo** para la flota de camiones
794AC de la mina Quellaveco. Los modelos de Machine Learning ya están entrenados y
guardados como archivos `.pkl`. El objetivo de este backend es:

1. **Servir predicciones** a partir de los modelos entrenados
2. **Gestionar el historial** de muestras usando Excel como base de datos (MVP)
3. **Registrar nuevas muestras** y recalcular predicciones automáticamente
4. **Exponer endpoints REST** que el frontend Streamlit consumirá

---

## ESTRUCTURA DE ARCHIVOS EXISTENTE

```
proyecto/
├── models/
│   ├── clasificador_estado_xgboost.pkl     ← Clasificador de estado (NORMAL/PRECAUCION/CRITICO)
│   ├── estimador_horas_hasta_critico.pkl   ← Estimador de horas hasta estado crítico
│   ├── regresor_TBN_(mg_KOH_g).pkl         ← Regresores de variables t+1
│   ├── regresor_Hollin_ABS_01_mm.pkl
│   ├── regresor_Fierro_ppm.pkl
│   ├── regresor_Viscosidad_a_100_degC_cSt.pkl
│   ├── regresor_Oxidación_ABS_01_mm.pkl
│   ├── regresor_Sulfatación_ABS_01_mm.pkl
│   ├── regresor_Nitración_ABS_01_mm.pkl
│   ├── regresor_Cobre_ppm.pkl
│   ├── regresor_Potasio_ppm.pkl
│   ├── regresor_Silicio_ppm.pkl
│   ├── regresor_Aluminio_ppm.pkl
│   └── feat_cols.json                      ← Lista de 173 features exactas del modelo
│
├── data/
│   └── DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx  ← Base de datos principal
│
├── backend/
│   ├── main.py                ← App FastAPI principal  (CREAR)
│   ├── models_loader.py       ← Carga de modelos pkl  (CREAR)
│   ├── feature_builder.py     ← Construcción de features  (CREAR)
│   ├── excel_manager.py       ← Gestión de Excel como DB  (CREAR)
│   ├── predictor.py           ← Lógica de predicción  (CREAR)
│   └── schemas.py             ← Modelos Pydantic  (CREAR)
```

---

## VARIABLES CLAVE DEL SISTEMA

```python
# Variables en las que los modelos fueron entrenados
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

# Columnas del Excel original (hoja '794AC QUELLA')
COLUMNAS_EXCEL = [
    'Codigo', 'Fecha', 'Fecha - Año', 'Equipo', 'PRUEBA',
    'Hora_Producto', 'Producto', 'Estado',
    'TBN (mg KOH/g)', 'Viscosidad a 40 °C cSt', 'Viscosidad a 100 °C cSt',
    'Oxidación ABS/01 mm', 'Nitración ABS/01 mm', 'Sulfatación ABS/01 mm',
    'Hollin ABS/01 mm', 'Glycol %', 'Diesel %', 'Agua %',
    'AGUA (CRAQUEO) TRAZ/NEG  ', 'Indice de Viscosidad', 'Agua ppm',
    'Magnesio ppm', 'Calcio ppm', 'Zinc ppm', 'Vanadio ppm',
    'Fosforo ppm', 'Molibdeno ppm', 'Manganeso ppm', 'Fierro ppm',
    'TD Fe', 'Cromo ppm', 'Plomo ppm', 'TD Pb', 'Cobre ppm', 'TD Cu',
    'Estaño ppm', 'Aluminio ppm', 'Niquel ppm', 'Plata ppm',
    'Litio ppm', 'Antimonio ppm', 'Titanio ppm', 'Cadmio ppm',
    'Silicio ppm', 'Potasio ppm', 'Boro ppm', 'Sodio ppm', 'Bario  ppm',
    'Particulas Ferrosas (PQ) ', 'Fe Acum ppm', 'Cr Acum ppm',
    'Pb Acum ppm', 'Cu Acum ppm', 'Sn Acum ppm', 'Al Acum ppm',
    'Si Acum ppm', 'Observacion', 'Accion_Sugerida'
]

# Umbrales de alerta operativa
LIMITES_ALERTA = {
    'TBN (mg KOH/g)':        {'precaucion': 8.0,  'critico': 7.5,  'dir': 'lower'},
    'Viscosidad a 100 °C cSt':{'precaucion': 13.0, 'critico': 12.5, 'dir': 'lower'},
    'Hollin ABS/01 mm':      {'precaucion': 0.70,  'critico': 1.00, 'dir': 'upper'},
    'Fierro ppm':            {'precaucion': 30,    'critico': 50,   'dir': 'upper'},
    'Cobre ppm':             {'precaucion': 10,    'critico': 20,   'dir': 'upper'},
    'Silicio ppm':           {'precaucion': 15,    'critico': 25,   'dir': 'upper'},
    'Potasio ppm':           {'precaucion': 3,     'critico': 5,    'dir': 'upper'},
    'Oxidación ABS/01 mm':   {'precaucion': 0.10,  'critico': 0.15, 'dir': 'upper'},
}

# Parámetros de features (DEBEN coincidir exactamente con los usados en Fase 2)
N_LAGS = 5
ESTADO_MAP = {'NORMAL': 0, 'PRECAUCION': 1, 'CRITICO': 2}
ESTADO_MAP_INV = {0: 'NORMAL', 1: 'PRECAUCION', 2: 'CRITICO'}
HORA_QUIEBRE_AMARILLO = 300   # horas — zona de precaución
HORA_QUIEBRE_ROJO = 450       # horas — zona crítica
```

---

## INSTRUCCIONES GENERALES

Crea los siguientes **6 archivos Python** dentro de la carpeta `backend/`.
Usa **FastAPI** como framework. Instalar dependencias:

```bash
pip install fastapi uvicorn pandas openpyxl joblib scikit-learn lightgbm xgboost pydantic python-multipart
```

---

## ARCHIVO 1: `backend/schemas.py`

Define todos los modelos Pydantic de request/response.

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

# ── REQUEST SCHEMAS ──────────────────────────────────────────────────

class NuevaMuestraRequest(BaseModel):
    """Schema para registrar una nueva muestra de aceite."""
    equipo: str = Field(..., example="HT012", description="ID del camión (ej: HT001)")
    fecha: str = Field(..., example="2024-04-01", description="Fecha de la muestra (YYYY-MM-DD)")
    hora_producto: float = Field(..., example=450.0, description="Horas de servicio del aceite")
    producto: str = Field(default="RIMULA R4 L 15W40", description="Nombre del lubricante")

    # Variables analíticas (todas opcionales — se acepta muestra parcial)
    tbn: Optional[float] = Field(None, alias="TBN (mg KOH/g)", example=8.1)
    viscosidad_100: Optional[float] = Field(None, alias="Viscosidad a 100 °C cSt", example=13.4)
    hollin: Optional[float] = Field(None, alias="Hollin ABS/01 mm", example=0.65)
    fierro: Optional[float] = Field(None, alias="Fierro ppm", example=22.0)
    oxidacion: Optional[float] = Field(None, alias="Oxidación ABS/01 mm", example=0.04)
    sulfatacion: Optional[float] = Field(None, alias="Sulfatación ABS/01 mm", example=0.02)
    nitracion: Optional[float] = Field(None, alias="Nitración ABS/01 mm", example=0.01)
    cobre: Optional[float] = Field(None, alias="Cobre ppm", example=1.5)
    potasio: Optional[float] = Field(None, alias="Potasio ppm", example=0.5)
    silicio: Optional[float] = Field(None, alias="Silicio ppm", example=8.0)
    aluminio: Optional[float] = Field(None, alias="Aluminio ppm", example=1.2)
    cromo: Optional[float] = Field(None, alias="Cromo ppm", example=0.0)
    observacion: Optional[str] = Field(None, description="Observación del analista")

    class Config:
        populate_by_name = True


class PrediccionRequest(BaseModel):
    """Schema para solicitar predicción sin registrar muestra."""
    equipo: str = Field(..., example="HT012")
    usar_ultimas_n: int = Field(default=10, description="Cuántas muestras históricas usar")


# ── RESPONSE SCHEMAS ─────────────────────────────────────────────────

class ValoresPredichos(BaseModel):
    """Valores numéricos predichos para la próxima muestra."""
    tbn: Optional[float] = None
    viscosidad_100: Optional[float] = None
    hollin: Optional[float] = None
    fierro: Optional[float] = None
    oxidacion: Optional[float] = None
    sulfatacion: Optional[float] = None
    nitracion: Optional[float] = None
    cobre: Optional[float] = None
    potasio: Optional[float] = None
    silicio: Optional[float] = None
    aluminio: Optional[float] = None
    cromo: Optional[float] = None


class AlertaVariable(BaseModel):
    """Alerta individual de una variable que supera límite."""
    variable: str
    valor_actual: float
    limite_precaucion: Optional[float]
    limite_critico: Optional[float]
    nivel: str  # 'NORMAL', 'PRECAUCION', 'CRITICO'


class PrediccionResponse(BaseModel):
    """Respuesta completa de predicción para un equipo."""
    equipo: str
    hora_actual: float
    estado_actual: str
    estado_predicho: str
    probabilidades: Dict[str, float]
    horas_hasta_critico: Optional[float]
    nivel_alerta: str          # 'VERDE', 'AMARILLO', 'ROJO'
    mensaje_alerta: str
    valores_actuales: Dict[str, Optional[float]]
    valores_predichos: Dict[str, Optional[float]]
    alertas_variables: List[AlertaVariable]
    n_muestras_historial: int
    timestamp_prediccion: datetime
    confianza_modelo: str      # 'ALTA', 'MEDIA', 'BAJA' (según n muestras)


class EquipoResumen(BaseModel):
    """Resumen de estado de un equipo para el dashboard de flota."""
    equipo: str
    n_muestras: int
    ultima_muestra_fecha: Optional[str]
    ultima_hora_producto: Optional[float]
    estado_actual: Optional[str]
    estado_predicho: Optional[str]
    nivel_alerta: Optional[str]
    horas_hasta_critico: Optional[float]
    pct_muestras_criticas: float
    tbn_ultimo: Optional[float]
    hollin_ultimo: Optional[float]
    fierro_ultimo: Optional[float]


class FlotaResumenResponse(BaseModel):
    """Resumen de toda la flota para el dashboard principal."""
    total_equipos: int
    equipos_rojo: int
    equipos_amarillo: int
    equipos_verde: int
    equipos: List[EquipoResumen]
    timestamp: datetime


class HistorialResponse(BaseModel):
    """Historial de muestras de un equipo."""
    equipo: str
    n_muestras: int
    muestras: List[Dict[str, Any]]


class MuestraRegistradaResponse(BaseModel):
    """Respuesta al registrar una nueva muestra."""
    success: bool
    mensaje: str
    equipo: str
    fecha: str
    hora_producto: float
    prediccion: Optional[PrediccionResponse] = None
```

---

## ARCHIVO 2: `backend/excel_manager.py`

Gestiona el Excel como base de datos. Lee, escribe y actualiza muestras.

```python
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import threading
import os

# Lock para evitar race conditions al escribir en Excel
_excel_lock = threading.Lock()

EXCEL_PATH = Path("data/DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx")
SHEET_NAME = "794AC QUELLA"

# Mapeo de campos del schema a columnas del Excel
CAMPO_A_COLUMNA = {
    'tbn':           'TBN (mg KOH/g)',
    'viscosidad_100':'Viscosidad a 100 °C cSt',
    'hollin':        'Hollin ABS/01 mm',
    'fierro':        'Fierro ppm',
    'oxidacion':     'Oxidación ABS/01 mm',
    'sulfatacion':   'Sulfatación ABS/01 mm',
    'nitracion':     'Nitración ABS/01 mm',
    'cobre':         'Cobre ppm',
    'potasio':       'Potasio ppm',
    'silicio':       'Silicio ppm',
    'aluminio':      'Aluminio ppm',
    'cromo':         'Cromo ppm',
}


def cargar_datos() -> pd.DataFrame:
    """Carga la hoja principal del Excel y tipifica columnas."""
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Hora_Producto'] = pd.to_numeric(df['Hora_Producto'], errors='coerce')
    df['Equipo'] = df['Equipo'].astype(str).str.strip()

    # Convertir variables analíticas a numérico
    vars_numericas = list(CAMPO_A_COLUMNA.values())
    for col in vars_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df.sort_values(['Equipo', 'Hora_Producto']).reset_index(drop=True)


def obtener_historial_equipo(equipo: str, n_ultimas: int = None) -> pd.DataFrame:
    """
    Retorna el historial de muestras de un equipo específico.
    Si n_ultimas es None, retorna todo el historial.
    Ordenado por Hora_Producto ascendente.
    """
    df = cargar_datos()
    grp = df[df['Equipo'] == equipo].sort_values('Hora_Producto')
    if n_ultimas:
        grp = grp.tail(n_ultimas)
    return grp.reset_index(drop=True)


def obtener_todos_equipos() -> list:
    """Retorna lista de todos los equipos con al menos 1 muestra."""
    df = cargar_datos()
    return sorted(df['Equipo'].unique().tolist())


def obtener_resumen_equipo(equipo: str) -> dict:
    """
    Retorna estadísticas resumen de un equipo:
    - n_muestras, última fecha, última hora, estado actual,
    - % muestras críticas, últimos valores de variables clave.
    """
    grp = obtener_historial_equipo(equipo)
    if len(grp) == 0:
        return {'equipo': equipo, 'n_muestras': 0}

    ultima = grp.iloc[-1]
    pct_critico = (grp['Estado'] == 'CRITICO').sum() / len(grp) * 100

    return {
        'equipo': equipo,
        'n_muestras': len(grp),
        'ultima_muestra_fecha': str(ultima['Fecha'].date()) if pd.notna(ultima['Fecha']) else None,
        'ultima_hora_producto': float(ultima['Hora_Producto']) if pd.notna(ultima['Hora_Producto']) else None,
        'estado_actual': str(ultima['Estado']) if pd.notna(ultima.get('Estado')) else None,
        'pct_muestras_criticas': round(pct_critico, 1),
        'tbn_ultimo': float(ultima['TBN (mg KOH/g)']) if pd.notna(ultima.get('TBN (mg KOH/g)')) else None,
        'hollin_ultimo': float(ultima['Hollin ABS/01 mm']) if pd.notna(ultima.get('Hollin ABS/01 mm')) else None,
        'fierro_ultimo': float(ultima['Fierro ppm']) if pd.notna(ultima.get('Fierro ppm')) else None,
    }


def registrar_nueva_muestra(muestra_dict: dict) -> bool:
    """
    Agrega una nueva fila al Excel con los datos de la nueva muestra.
    Usa lock para evitar escrituras concurrentes.
    Retorna True si se guardó exitosamente.
    """
    with _excel_lock:
        try:
            df = cargar_datos()

            # Construir nueva fila
            fecha_dt = pd.to_datetime(muestra_dict.get('fecha'))
            nueva_fila = {
                'Codigo': f"MVP_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'Fecha': fecha_dt,
                'Fecha - Año': f"{fecha_dt.month}-{fecha_dt.year}",
                'Equipo': muestra_dict['equipo'],
                'Hora_Producto': muestra_dict['hora_producto'],
                'Producto': muestra_dict.get('producto', 'RIMULA R4 L 15W40'),
                'Estado': muestra_dict.get('estado_predicho', 'PRECAUCION'),
                'Observacion': muestra_dict.get('observacion', 'Ingresado vía SaaS MVP'),
            }

            # Agregar variables analíticas
            for campo, columna in CAMPO_A_COLUMNA.items():
                nueva_fila[columna] = muestra_dict.get(campo)

            # Agregar fila al dataframe
            nueva_fila_df = pd.DataFrame([nueva_fila])
            df_actualizado = pd.concat([df, nueva_fila_df], ignore_index=True)

            # Guardar de vuelta al Excel (preservar otras hojas)
            with pd.ExcelWriter(
                EXCEL_PATH,
                engine='openpyxl',
                mode='a',
                if_sheet_exists='replace'
            ) as writer:
                df_actualizado.to_excel(writer, sheet_name=SHEET_NAME, index=False)

            return True

        except Exception as e:
            print(f"Error guardando en Excel: {e}")
            return False
```

---

## ARCHIVO 3: `backend/feature_builder.py`

Construye el vector de features para el modelo.
**CRÍTICO: debe producir exactamente las mismas 173 features que en el entrenamiento.**

```python
import pandas as pd
import numpy as np
import json
from pathlib import Path

# Cargar la lista exacta de features usadas en el entrenamiento
with open(Path("models/feat_cols.json"), "r") as f:
    FEAT_COLS = json.load(f)

N_LAGS = 5
VARS_LAG = [
    'TBN (mg KOH/g)', 'Viscosidad a 100 °C cSt', 'Hollin ABS/01 mm',
    'Fierro ppm', 'Oxidación ABS/01 mm', 'Sulfatación ABS/01 mm',
    'Nitración ABS/01 mm', 'Cobre ppm', 'Potasio ppm',
    'Silicio ppm', 'Aluminio ppm', 'Cromo ppm',
]
ESTADO_MAP = {'NORMAL': 0, 'PRECAUCION': 1, 'CRITICO': 2}


def build_feature_vector(historial: pd.DataFrame) -> pd.DataFrame:
    """
    Dado el historial de un equipo (ordenado por Hora_Producto),
    construye el vector de features para la última muestra disponible.

    Este es el equivalente de build_features() de la Fase 2,
    aplicado solo al último punto del historial.

    Args:
        historial: DataFrame con al menos N_LAGS+1 filas, columnas de VARS_LAG,
                   'Hora_Producto', 'Estado', ordenado por Hora_Producto asc.

    Returns:
        DataFrame de 1 fila con exactamente FEAT_COLS columnas.
    """
    if len(historial) < 2:
        raise ValueError(f"Se necesitan al menos 2 muestras, se recibieron {len(historial)}")

    grp = historial.sort_values('Hora_Producto').copy().reset_index(drop=True)
    n = len(grp)

    features = {}

    for var in VARS_LAG:
        if var not in grp.columns:
            # Variable ausente: rellenar con NaN
            for k in range(1, N_LAGS + 1):
                features[f'lag{k}_{var[:18]}'] = np.nan
            for k in range(1, N_LAGS):
                features[f'delta{k}_{var[:18]}'] = np.nan
            for w in [3, 5]:
                features[f'rollmean{w}_{var[:15]}'] = np.nan
                features[f'rollstd{w}_{var[:15]}'] = np.nan
            features[f'trend_{var[:18]}'] = np.nan
            continue

        s = pd.to_numeric(grp[var], errors='coerce').values

        # Lags: t usa el valor de t-1 (último valor disponible = índice -1)
        for k in range(1, N_LAGS + 1):
            idx = -(k)
            features[f'lag{k}_{var[:18]}'] = (
                float(s[idx]) if abs(idx) <= len(s) and not np.isnan(s[idx])
                else np.nan
            )

        # Deltas entre lags consecutivos
        for k in range(1, N_LAGS):
            v_k   = s[-(k)]   if len(s) >= k   else np.nan
            v_k1  = s[-(k+1)] if len(s) >= k+1 else np.nan
            features[f'delta{k}_{var[:18]}'] = (
                float(v_k - v_k1)
                if not (np.isnan(v_k) or np.isnan(v_k1)) else np.nan
            )

        # Rolling mean y std de las últimas 3 y 5 muestras PREVIAS (sin incluir t)
        prev = s[:-1]  # excluir el último punto (que es "t" actual, no previo)
        for w in [3, 5]:
            window = prev[-w:] if len(prev) >= w else prev
            features[f'rollmean{w}_{var[:15]}'] = (
                float(np.nanmean(window)) if len(window) > 0 else np.nan
            )
            features[f'rollstd{w}_{var[:15]}'] = (
                float(np.nanstd(window)) if len(window) > 1 else 0.0
            )

        # Tendencia lineal (pendiente) de las últimas 3 muestras previas
        trend_data = prev[-3:] if len(prev) >= 3 else prev
        valid = ~np.isnan(trend_data)
        if valid.sum() >= 2:
            xi = np.arange(len(trend_data))
            slope = np.polyfit(xi[valid], trend_data[valid], 1)[0]
            features[f'trend_{var[:18]}'] = float(slope)
        else:
            features[f'trend_{var[:18]}'] = np.nan

    # Features de contexto
    features['horas_actuales']     = float(grp['Hora_Producto'].iloc[-1])
    features['horas_desde_ultima'] = (
        float(grp['Hora_Producto'].iloc[-1] - grp['Hora_Producto'].iloc[-2])
        if len(grp) >= 2 else np.nan
    )
    features['es_cambio_aceite']   = 0

    estados_num = grp['Estado'].map(ESTADO_MAP)
    features['estado_lag1'] = float(estados_num.iloc[-1]) if len(estados_num) >= 1 else np.nan
    features['estado_lag2'] = float(estados_num.iloc[-2]) if len(estados_num) >= 2 else np.nan

    # Construir DataFrame con exactamente las columnas de FEAT_COLS
    X = pd.DataFrame([features])

    # Agregar columnas faltantes como 0 (para compatibilidad con el modelo)
    for col in FEAT_COLS:
        if col not in X.columns:
            X[col] = 0.0

    # Seleccionar en el orden exacto del entrenamiento
    X = X[FEAT_COLS].fillna(0.0)

    return X


def calcular_confianza(n_muestras: int) -> str:
    """Califica la confianza del modelo según cuántas muestras hay."""
    if n_muestras >= 30:
        return 'ALTA'
    elif n_muestras >= 10:
        return 'MEDIA'
    else:
        return 'BAJA'
```

---

## ARCHIVO 4: `backend/models_loader.py`

Carga todos los modelos al iniciar la app (singleton pattern).

```python
import joblib
import json
from pathlib import Path
from functools import lru_cache

MODELS_DIR = Path("models")

# Nombres de archivos de regresores (mapeo variable → archivo)
REGRESOR_FILES = {
    'TBN (mg KOH/g)':           'regresor_TBN_(mg_KOH_g).pkl',
    'Viscosidad a 100 °C cSt':  'regresor_Viscosidad_a_100_degC_cSt.pkl',
    'Hollin ABS/01 mm':         'regresor_Hollin_ABS_01_mm.pkl',
    'Fierro ppm':               'regresor_Fierro_ppm.pkl',
    'Oxidación ABS/01 mm':      'regresor_Oxidación_ABS_01_mm.pkl',
    'Sulfatación ABS/01 mm':    'regresor_Sulfatación_ABS_01_mm.pkl',
    'Nitración ABS/01 mm':      'regresor_Nitración_ABS_01_mm.pkl',
    'Cobre ppm':                'regresor_Cobre_ppm.pkl',
    'Potasio ppm':              'regresor_Potasio_ppm.pkl',
    'Silicio ppm':              'regresor_Silicio_ppm.pkl',
    'Aluminio ppm':             'regresor_Aluminio_ppm.pkl',
    'Cromo ppm':                'regresor_Cromo_ppm.pkl',
}


class ModelsLoader:
    """Carga y cachea todos los modelos una sola vez al iniciar el servidor."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load_all(self):
        if self._loaded:
            return
        print("Cargando modelos ML...")

        # Clasificador principal
        clf_path = MODELS_DIR / 'clasificador_estado_xgboost.pkl'
        self.clasificador = joblib.load(clf_path)
        print(f"  ✓ Clasificador: {clf_path.name}")

        # Estimador de supervivencia
        surv_path = MODELS_DIR / 'estimador_horas_hasta_critico.pkl'
        self.survival_model = joblib.load(surv_path)
        print(f"  ✓ Supervivencia: {surv_path.name}")

        # Regresores por variable
        self.regresores = {}
        for var, filename in REGRESOR_FILES.items():
            path = MODELS_DIR / filename
            if path.exists():
                self.regresores[var] = joblib.load(path)
                print(f"  ✓ Regresor: {filename}")
            else:
                print(f"  ⚠ No encontrado: {filename}")

        # Lista de features
        with open(MODELS_DIR / 'feat_cols.json', 'r') as f:
            self.feat_cols = json.load(f)
        print(f"  ✓ feat_cols.json: {len(self.feat_cols)} features")

        self._loaded = True
        print("✓ Todos los modelos cargados correctamente.\n")


# Instancia global
models = ModelsLoader()
```

---

## ARCHIVO 5: `backend/predictor.py`

Lógica central de predicción. Orquesta feature builder + modelos.

```python
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from .models_loader import models
from .feature_builder import build_feature_vector, calcular_confianza
from .excel_manager import obtener_historial_equipo

ESTADO_MAP_INV = {0: 'NORMAL', 1: 'PRECAUCION', 2: 'CRITICO'}

LIMITES_ALERTA = {
    'TBN (mg KOH/g)':         {'precaucion': 8.0,  'critico': 7.5,  'dir': 'lower'},
    'Viscosidad a 100 °C cSt': {'precaucion': 13.0, 'critico': 12.5, 'dir': 'lower'},
    'Hollin ABS/01 mm':        {'precaucion': 0.70, 'critico': 1.00, 'dir': 'upper'},
    'Fierro ppm':              {'precaucion': 30,   'critico': 50,   'dir': 'upper'},
    'Cobre ppm':               {'precaucion': 10,   'critico': 20,   'dir': 'upper'},
    'Silicio ppm':             {'precaucion': 15,   'critico': 25,   'dir': 'upper'},
    'Potasio ppm':             {'precaucion': 3,    'critico': 5,    'dir': 'upper'},
    'Oxidación ABS/01 mm':     {'precaucion': 0.10, 'critico': 0.15, 'dir': 'upper'},
}


def evaluar_alertas_variables(valores: dict) -> list:
    """
    Evalúa cada variable contra sus límites y retorna lista de alertas.
    """
    alertas = []
    for var, limites in LIMITES_ALERTA.items():
        val = valores.get(var)
        if val is None or np.isnan(float(val if val is not None else np.nan)):
            continue
        val = float(val)
        nivel = 'NORMAL'
        if limites['dir'] == 'upper':
            if val >= limites['critico']:
                nivel = 'CRITICO'
            elif val >= limites['precaucion']:
                nivel = 'PRECAUCION'
        else:  # lower
            if val <= limites['critico']:
                nivel = 'CRITICO'
            elif val <= limites['precaucion']:
                nivel = 'PRECAUCION'
        if nivel != 'NORMAL':
            alertas.append({
                'variable': var,
                'valor_actual': val,
                'limite_precaucion': limites['precaucion'],
                'limite_critico': limites['critico'],
                'nivel': nivel,
            })
    return alertas


def determinar_semaforo(estado_predicho: str,
                        horas_hasta_critico: Optional[float],
                        hora_actual: float) -> tuple:
    """
    Determina el nivel de alerta semafórico y el mensaje.
    Combina la predicción del modelo con las horas acumuladas.
    """
    # Factor de horas acumuladas (umbral conocido de la Fase 1)
    alerta_por_horas = 'VERDE'
    if hora_actual >= 450:
        alerta_por_horas = 'ROJO'
    elif hora_actual >= 300:
        alerta_por_horas = 'AMARILLO'

    # Factor de predicción del modelo
    alerta_por_modelo = 'VERDE'
    if estado_predicho == 'CRITICO':
        alerta_por_modelo = 'ROJO'
    elif estado_predicho == 'PRECAUCION':
        alerta_por_modelo = 'AMARILLO'

    # Factor de horas restantes
    alerta_por_survival = 'VERDE'
    if horas_hasta_critico is not None:
        if horas_hasta_critico < 80:
            alerta_por_survival = 'ROJO'
        elif horas_hasta_critico < 200:
            alerta_por_survival = 'AMARILLO'

    # Tomar el peor de los tres
    niveles = {'VERDE': 0, 'AMARILLO': 1, 'ROJO': 2}
    peor = max([alerta_por_horas, alerta_por_modelo, alerta_por_survival],
               key=lambda x: niveles[x])

    mensajes = {
        'ROJO': (
            f'🔴 ALERTA CRÍTICA — Estado predicho: {estado_predicho}. '
            f'Horas acumuladas: {hora_actual:.0f}h. '
            f'{"Tiempo estimado hasta crítico: " + str(round(horas_hasta_critico)) + "h." if horas_hasta_critico else ""} '
            'Revisar inmediatamente y considerar cambio de aceite.'
        ),
        'AMARILLO': (
            f'🟡 PRECAUCIÓN — Estado predicho: {estado_predicho}. '
            f'Horas acumuladas: {hora_actual:.0f}h. '
            f'{"Horas estimadas hasta crítico: " + str(round(horas_hasta_critico)) + "h." if horas_hasta_critico else ""} '
            'Aumentar frecuencia de muestreo.'
        ),
        'VERDE': (
            f'🟢 NORMAL — Estado predicho: {estado_predicho}. '
            f'Horas acumuladas: {hora_actual:.0f}h. '
            'Continuar con el plan de muestreo regular.'
        ),
    }

    return peor, mensajes[peor]


def predecir_equipo(equipo: str, n_ultimas: int = 15) -> dict:
    """
    Función principal de predicción.
    Dado un equipo, retorna el dict completo de predicción.
    """
    # 1. Cargar historial
    historial = obtener_historial_equipo(equipo, n_ultimas=n_ultimas)
    n_muestras = len(historial)

    if n_muestras < 2:
        return {
            'equipo': equipo,
            'error': f'Historial insuficiente: {n_muestras} muestras (mínimo 2)',
            'nivel_alerta': 'GRIS',
            'mensaje_alerta': 'Sin datos suficientes para predicción.',
        }

    ultima = historial.iloc[-1]
    hora_actual = float(ultima['Hora_Producto']) if pd.notna(ultima['Hora_Producto']) else 0.0
    estado_actual = str(ultima['Estado']) if pd.notna(ultima.get('Estado')) else 'DESCONOCIDO'

    # 2. Construir vector de features
    try:
        X = build_feature_vector(historial)
    except Exception as e:
        return {'equipo': equipo, 'error': f'Error construyendo features: {e}',
                'nivel_alerta': 'GRIS', 'mensaje_alerta': str(e)}

    # 3. Predicción de estado
    estado_cod = int(models.clasificador.predict(X)[0])
    estado_predicho = ESTADO_MAP_INV.get(estado_cod, 'DESCONOCIDO')

    probabilidades = {}
    if hasattr(models.clasificador, 'predict_proba'):
        probs = models.clasificador.predict_proba(X)[0]
        for i, nombre in ESTADO_MAP_INV.items():
            if i < len(probs):
                probabilidades[nombre] = round(float(probs[i]), 4)

    # 4. Predicción de horas hasta crítico
    try:
        horas_critico = float(models.survival_model.predict(X)[0])
        horas_critico = max(0.0, horas_critico)
    except Exception:
        horas_critico = None

    # 5. Predicción de valores t+1
    vars_numericas = [
        'TBN (mg KOH/g)', 'Viscosidad a 100 °C cSt', 'Hollin ABS/01 mm',
        'Fierro ppm', 'Oxidación ABS/01 mm', 'Sulfatación ABS/01 mm',
        'Nitración ABS/01 mm', 'Cobre ppm', 'Potasio ppm',
        'Silicio ppm', 'Aluminio ppm', 'Cromo ppm',
    ]
    valores_predichos = {}
    for var in vars_numericas:
        reg = models.regresores.get(var)
        if reg is not None:
            try:
                valores_predichos[var] = round(float(reg.predict(X)[0]), 4)
            except Exception:
                valores_predichos[var] = None
        else:
            valores_predichos[var] = None

    # 6. Valores actuales del último registro
    valores_actuales = {}
    for var in vars_numericas:
        v = ultima.get(var)
        valores_actuales[var] = float(v) if pd.notna(v) else None

    # 7. Alertas por variable (valores actuales vs límites)
    alertas = evaluar_alertas_variables(valores_actuales)

    # 8. Semáforo
    nivel_alerta, mensaje = determinar_semaforo(estado_predicho, horas_critico, hora_actual)

    return {
        'equipo': equipo,
        'hora_actual': hora_actual,
        'estado_actual': estado_actual,
        'estado_predicho': estado_predicho,
        'probabilidades': probabilidades,
        'horas_hasta_critico': round(horas_critico, 1) if horas_critico is not None else None,
        'nivel_alerta': nivel_alerta,
        'mensaje_alerta': mensaje,
        'valores_actuales': valores_actuales,
        'valores_predichos': valores_predichos,
        'alertas_variables': alertas,
        'n_muestras_historial': n_muestras,
        'timestamp_prediccion': datetime.now(),
        'confianza_modelo': calcular_confianza(n_muestras),
    }
```

---

## ARCHIVO 6: `backend/main.py`

App FastAPI principal con todos los endpoints.

```python
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional
import pandas as pd
import io

from .schemas import (
    NuevaMuestraRequest, PrediccionRequest,
    PrediccionResponse, FlotaResumenResponse,
    EquipoResumen, HistorialResponse, MuestraRegistradaResponse
)
from .models_loader import models
from .predictor import predecir_equipo
from .excel_manager import (
    obtener_todos_equipos, obtener_resumen_equipo,
    obtener_historial_equipo, registrar_nueva_muestra, cargar_datos
)

# ── Inicializar FastAPI ───────────────────────────────────────────────
app = FastAPI(
    title="SaaS Predictivo de Aceites — Flota 794AC Quellaveco",
    description=(
        "API REST para monitoreo predictivo de aceite de motor en camiones 794AC. "
        "Predice estado futuro (NORMAL/PRECAUCIÓN/CRÍTICO), valores analíticos t+1 "
        "y horas estimadas hasta estado crítico."
    ),
    version="1.0.0-MVP",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (permite que Streamlit en localhost acceda) ──────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # En producción: especificar el dominio de Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Cargar modelos al iniciar ─────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    models.load_all()
    print("✓ API lista para recibir requests.")


# ── ENDPOINT: Health Check ────────────────────────────────────────────
@app.get("/health", tags=["Sistema"])
def health_check():
    """Verifica que la API y los modelos estén operativos."""
    return {
        "status": "ok",
        "version": "1.0.0-MVP",
        "modelos_cargados": models._loaded,
        "n_regresores": len(models.regresores) if models._loaded else 0,
        "timestamp": datetime.now().isoformat(),
    }


# ── ENDPOINT: Dashboard de Flota ─────────────────────────────────────
@app.get("/flota/resumen", response_model=FlotaResumenResponse, tags=["Flota"])
def resumen_flota():
    """
    Retorna el estado predictivo de TODA la flota de camiones.
    Usado por el dashboard principal del SaaS.
    Genera una predicción por cada equipo con historial suficiente.
    """
    equipos = obtener_todos_equipos()
    resumen_equipos = []
    rojo = amarillo = verde = 0

    for equipo in equipos:
        try:
            pred = predecir_equipo(equipo, n_ultimas=15)
            nivel = pred.get('nivel_alerta', 'GRIS')

            if nivel == 'ROJO':    rojo += 1
            elif nivel == 'AMARILLO': amarillo += 1
            elif nivel == 'VERDE':    verde += 1

            resumen_equipos.append(EquipoResumen(
                equipo=equipo,
                n_muestras=pred.get('n_muestras_historial', 0),
                ultima_muestra_fecha=str(obtener_historial_equipo(equipo, 1).iloc[-1]['Fecha'].date())
                                     if len(obtener_historial_equipo(equipo, 1)) > 0 else None,
                ultima_hora_producto=pred.get('hora_actual'),
                estado_actual=pred.get('estado_actual'),
                estado_predicho=pred.get('estado_predicho'),
                nivel_alerta=nivel,
                horas_hasta_critico=pred.get('horas_hasta_critico'),
                pct_muestras_criticas=obtener_resumen_equipo(equipo).get('pct_muestras_criticas', 0.0),
                tbn_ultimo=pred.get('valores_actuales', {}).get('TBN (mg KOH/g)'),
                hollin_ultimo=pred.get('valores_actuales', {}).get('Hollin ABS/01 mm'),
                fierro_ultimo=pred.get('valores_actuales', {}).get('Fierro ppm'),
            ))
        except Exception as e:
            print(f"Error procesando {equipo}: {e}")

    return FlotaResumenResponse(
        total_equipos=len(equipos),
        equipos_rojo=rojo,
        equipos_amarillo=amarillo,
        equipos_verde=verde,
        equipos=resumen_equipos,
        timestamp=datetime.now(),
    )


# ── ENDPOINT: Predicción individual ──────────────────────────────────
@app.get("/equipos/{equipo}/prediccion", tags=["Equipos"])
def prediccion_equipo(equipo: str, n_ultimas: int = 15):
    """
    Retorna predicción completa para un equipo específico:
    estado t+1, valores numéricos t+1, horas hasta crítico, semáforo.
    """
    resultado = predecir_equipo(equipo, n_ultimas=n_ultimas)
    if 'error' in resultado and resultado.get('nivel_alerta') == 'GRIS':
        raise HTTPException(status_code=404, detail=resultado['error'])
    return resultado


# ── ENDPOINT: Historial de muestras ──────────────────────────────────
@app.get("/equipos/{equipo}/historial", tags=["Equipos"])
def historial_equipo(equipo: str, n_ultimas: Optional[int] = None):
    """
    Retorna el historial de muestras de un equipo.
    Si n_ultimas es None, retorna todo el historial.
    """
    df = obtener_historial_equipo(equipo, n_ultimas=n_ultimas)
    if len(df) == 0:
        raise HTTPException(status_code=404, detail=f"Equipo {equipo} no encontrado.")
    records = df.fillna('').to_dict(orient='records')
    return {
        'equipo': equipo,
        'n_muestras': len(df),
        'muestras': records,
    }


# ── ENDPOINT: Lista de equipos ────────────────────────────────────────
@app.get("/equipos", tags=["Equipos"])
def listar_equipos():
    """Lista todos los equipos disponibles en la base de datos."""
    equipos = obtener_todos_equipos()
    return {"equipos": equipos, "total": len(equipos)}


# ── ENDPOINT: Registrar nueva muestra ────────────────────────────────
@app.post("/equipos/{equipo}/muestras", tags=["Muestras"])
def registrar_muestra(equipo: str, muestra: NuevaMuestraRequest):
    """
    Registra una nueva muestra de aceite para un equipo y
    retorna la predicción actualizada inmediatamente.
    """
    muestra_dict = muestra.dict(by_alias=False)
    muestra_dict['equipo'] = equipo

    # Guardar en Excel
    ok = registrar_nueva_muestra(muestra_dict)
    if not ok:
        raise HTTPException(status_code=500, detail="Error guardando la muestra en la base de datos.")

    # Generar predicción actualizada
    prediccion = predecir_equipo(equipo, n_ultimas=15)

    return {
        'success': True,
        'mensaje': f'Muestra registrada exitosamente para {equipo}.',
        'equipo': equipo,
        'fecha': muestra.fecha,
        'hora_producto': muestra.hora_producto,
        'prediccion': prediccion,
    }


# ── ENDPOINT: Subir Excel completo ────────────────────────────────────
@app.post("/datos/importar-excel", tags=["Datos"])
async def importar_excel(file: UploadFile = File(...)):
    """
    Permite subir un archivo Excel completo para reemplazar/actualizar
    la base de datos. Útil para importar lotes de nuevas muestras.
    Valida que el archivo tenga la hoja '794AC QUELLA' con las columnas correctas.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx o .xls")

    contents = await file.read()
    try:
        df_nuevo = pd.read_excel(io.BytesIO(contents), sheet_name='794AC QUELLA')
        n_filas = len(df_nuevo)
        n_equipos = df_nuevo['Equipo'].nunique() if 'Equipo' in df_nuevo.columns else 0
        return {
            'success': True,
            'mensaje': f'Excel validado: {n_filas} filas, {n_equipos} equipos. '
                       'Usa el endpoint de escritura para confirmar la importación.',
            'n_filas': n_filas,
            'n_equipos': n_equipos,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error leyendo el Excel: {e}")


# ── PUNTO DE ENTRADA ──────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## ARCHIVO EXTRA: `run_backend.py` (en la raíz del proyecto)

```python
"""Script para ejecutar el backend desde la raíz del proyecto."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,       # Auto-reload al cambiar código
        log_level="info",
    )
```

Para ejecutar:
```bash
python run_backend.py
# Luego abrir: http://localhost:8000/docs
```

---

## NOTAS FINALES PARA CURSOR

1. **Estructura de carpetas a crear:**
```
mkdir backend data models outputs_fase2 outputs_wavelet
touch backend/__init__.py
```

2. **`backend/__init__.py`** debe estar vacío pero presente para que Python reconozca el módulo.

3. **Nombres de archivos `.pkl`**: verificar que coincidan exactamente con los generados
   en Fase 2. Si difieren, ajustar el diccionario `REGRESOR_FILES` en `models_loader.py`.

4. **El endpoint `/flota/resumen` puede tardar** 10-30 segundos la primera vez porque
   genera predicciones para ~30 equipos. Agregar caché con `@lru_cache` o TTL de 5 min
   si el frontend lo llama frecuentemente.

5. **Probar con:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/equipos
curl http://localhost:8000/equipos/HT012/prediccion
```

6. **Documentación automática** en `http://localhost:8000/docs` (Swagger UI).
