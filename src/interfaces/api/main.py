"""OilMine Analytics — FastAPI app principal.

Puerto 8000. CORS habilitado para localhost:5173 (frontend Vite).

Al arrancar, la app:
  1. Precarga los 14 modelos ML (XGBoost + 12 LightGBM + HTC).
  2. Carga el Excel en memoria (usa snapshot Parquet si está fresco).
  3. Pre-computa /flota/resumen → primera visita del usuario es instantánea.

Eso elimina todos los 'warm-up costs' en el primer request real.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.settings import CORS_ORIGINS
from src.interfaces.api.dependencies import (
    get_excel_manager,
    get_modelo_loader,
    get_resumen_flota_uc,
)
from src.interfaces.api.routers import router

logger = logging.getLogger("oilmine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()

    # 1. Modelos ML (los 14 .pkl)
    logger.info("Precargando modelos ML…")
    try:
        get_modelo_loader().precargar()
        logger.info(f"Modelos cargados en {time.perf_counter() - t0:.2f}s")
    except Exception as e:
        logger.error(f"Error precargando modelos: {e}")

    # 2. Datos del Excel (o Parquet)
    t1 = time.perf_counter()
    try:
        get_excel_manager().preload()
        logger.info(f"Datos preload en {time.perf_counter() - t1:.2f}s")
    except Exception as e:
        logger.error(f"Error precargando datos: {e}")

    # 3. Warm-up /flota/resumen (33 predicciones)
    t2 = time.perf_counter()
    try:
        get_resumen_flota_uc().warm_up()
        logger.info(
            f"Warm-up /flota/resumen en {time.perf_counter() - t2:.2f}s "
            f"(cache listo)"
        )
    except Exception as e:
        logger.warning(f"Warm-up de flota falló (no bloquea arranque): {e}")

    logger.info(f"App lista en {time.perf_counter() - t0:.2f}s totales.")
    yield


app = FastAPI(
    title="OilMine Analytics API",
    description=(
        "Sistema predictivo de mantenimiento — Flota 794AC Quellaveco. "
        "Clasifica estado, predice la próxima muestra y estima horas "
        "hasta CRITICO."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],   # dev: aceptamos cualquier origen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["health"])
def root():
    return {
        "name": "OilMine Analytics",
        "docs": "/docs",
        "health": "/health",
    }
