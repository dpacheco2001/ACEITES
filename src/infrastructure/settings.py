"""Configuración central — paths, puertos, parámetros.

Todo path es relativo a la raíz del proyecto (ACEITES_MINERIA/).
"""
import os
from pathlib import Path

# ------------------------------------------------------------------
# Rutas
# ------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent.parent   # ACEITES_MINERIA/

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass
EXCEL_PATH = ROOT_DIR / "DATA FLOTA 794AC - MOTOR ORIGINAL QUELLAVECO_R4L 2024.xlsx"
EXCEL_FILENAME = EXCEL_PATH.name
EXCEL_SHEET = "794AC QUELLA"

# Datos aislados por empresa (dominio de correo)
TENANTS_ROOT = ROOT_DIR / "data" / "tenants"
AUTH_DB_PATH = ROOT_DIR / "data" / "auth.sqlite3"

# Google OAuth (GIS) + sesión JWT
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
# Tolerancia de reloj al verificar el ID token (evita "Token used too early" si el PC va unos s atrasado).
GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS = int(os.getenv("GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS", "120"))
JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-change-me").strip()
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

MODELS_DIR = ROOT_DIR / "models"
CLASIFICADOR_PATH = MODELS_DIR / "clasificador_estado_xgboost.pkl"
ESTIMADOR_PATH = MODELS_DIR / "estimador_horas_hasta_critico.pkl"
FEAT_COLS_PATH = MODELS_DIR / "feat_cols.json"


# ------------------------------------------------------------------
# Variables analíticas — NOMBRE EXACTO de la columna en Excel
# (orden crítico: debe coincidir con el usado en el entrenamiento)
# ------------------------------------------------------------------
VARIABLES_ANALITICAS = [
    "TBN (mg KOH/g)",
    "Viscosidad a 100 °C cSt",
    "Hollin ABS/01 mm",
    "Fierro ppm",
    "Oxidación ABS/01 mm",
    "Sulfatación ABS/01 mm",
    "Nitración ABS/01 mm",
    "Cobre ppm",
    "Potasio ppm",
    "Silicio ppm",
    "Aluminio ppm",
    "Cromo ppm",
]

# Variables con R² negativo → baja confianza
VARIABLES_BAJA_CONFIANZA = ["Potasio ppm", "Cromo ppm"]


# ------------------------------------------------------------------
# Feature-engineering (réplica exacta del notebook de entrenamiento)
# ------------------------------------------------------------------
N_LAGS = 5
ROLLING_WINDOWS = [3, 5]

ESTADO_MAP = {"NORMAL": 0, "PRECAUCION": 1, "CRITICO": 2}
ESTADO_INV = {v: k for k, v in ESTADO_MAP.items()}


# ------------------------------------------------------------------
# Mapeo de un nombre "seguro" (slug sin acentos/espacios) al nombre real
# de la variable en el Excel. Útil para la API (evita problemas de URL
# y de serialización JSON) y para resolver el archivo .pkl del regresor.
# ------------------------------------------------------------------
def safe_slug(var: str) -> str:
    """Reproduce la lógica del notebook de entrenamiento al guardar los .pkl."""
    return var.replace(" ", "_").replace("/", "_").replace("°", "deg")[:30]


VAR_TO_SLUG = {v: safe_slug(v) for v in VARIABLES_ANALITICAS}
SLUG_TO_VAR = {s: v for v, s in VAR_TO_SLUG.items()}


def regresor_path(var: str) -> Path:
    return MODELS_DIR / f"regresor_{safe_slug(var)}.pkl"


# ------------------------------------------------------------------
# API / CORS
# ------------------------------------------------------------------
API_PORT = 8000
FRONTEND_ORIGIN = "http://localhost:5173"
CORS_ORIGINS = [FRONTEND_ORIGIN, "http://127.0.0.1:5173"]


# ------------------------------------------------------------------
# Cache de predicciones
# ------------------------------------------------------------------
# TTL (segundos) para /flota/resumen y /equipos/{id}/prediccion.
# Se invalida explícitamente al registrar una muestra nueva, así que este
# TTL sólo afecta al caso "nadie escribe, muchos leen". 5 min es un
# balance razonable entre frescura y costo de re-cómputo.
PREDICCION_CACHE_TTL = 300.0


# ------------------------------------------------------------------
# Lógica de negocio validada (Sección 5 de la guía)
# ------------------------------------------------------------------
HORAS_UMBRAL_ROJO = 400
HORAS_UMBRAL_AMARILLO = 300
HORAS_HASTA_CRITICO_ROJO = 50
HORAS_HASTA_CRITICO_AMARILLO = 150

# Confianza del Modelo C (estimador horas hasta crítico).
# La guía indica: "confiable en rango 20-100h" (MAE 46.9h, R² 0.20).
HTC_CONFIANZA_MIN = 20.0
HTC_CONFIANZA_MAX = 100.0

# Historia mínima para que las predicciones sean defendibles.
# Se necesitan N_LAGS muestras para llenar todos los lags.
MUESTRAS_MINIMAS_CONFIABLES = 5


# ------------------------------------------------------------------
# Límites de alerta por variable (Sección 8 de la guía)
# (low_yellow, high_yellow, low_red, high_red) — None = sin límite
# Usado por el frontend para gauges; la API expone la tabla tal cual.
# ------------------------------------------------------------------
LIMITES_ALERTA = {
    "TBN (mg KOH/g)": {
        "direccion": "menor",          # mejor valor = alto
        "verde_min": 7.0, "verde_max": None,
        "amarillo_min": 5.0, "amarillo_max": 7.0,
        "rojo_max": 5.0,
    },
    "Viscosidad a 100 °C cSt": {
        "direccion": "rango",          # ideal en rango
        "verde_min": 13.0, "verde_max": 17.0,
        "amarillo_min": 11.0, "amarillo_max": 19.0,
        "rojo_max": 11.0, "rojo_min": 19.0,
    },
    "Hollin ABS/01 mm": {
        "direccion": "mayor",          # mejor valor = bajo
        "verde_max": 20, "amarillo_max": 35, "rojo_min": 35,
    },
    "Fierro ppm": {
        "direccion": "mayor",
        "verde_max": 40, "amarillo_max": 80, "rojo_min": 80,
    },
    "Cobre ppm": {
        "direccion": "mayor",
        "verde_max": 15, "amarillo_max": 30, "rojo_min": 30,
    },
    "Silicio ppm": {
        "direccion": "mayor",
        "verde_max": 15, "amarillo_max": 25, "rojo_min": 25,
    },
    "Oxidación ABS/01 mm": {
        "direccion": "mayor",
        "verde_max": 15, "amarillo_max": 25, "rojo_min": 25,
    },
    "Sulfatación ABS/01 mm": {
        "direccion": "mayor",
        "verde_max": 15, "amarillo_max": 25, "rojo_min": 25,
    },
    "Nitración ABS/01 mm": {
        "direccion": "mayor",
        "verde_max": 15, "amarillo_max": 25, "rojo_min": 25,
    },
    "Potasio ppm": {
        "direccion": "mayor",
        "verde_max": 5, "amarillo_max": 10, "rojo_min": 10,
    },
    "Aluminio ppm": {
        "direccion": "mayor",
        "verde_max": 10, "amarillo_max": 20, "rojo_min": 20,
    },
    "Cromo ppm": {
        "direccion": "mayor",
        "verde_max": 5, "amarillo_max": 10, "rojo_min": 10,
    },
}
