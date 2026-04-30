"""OilMine Analytics — FastAPI app principal.

Puerto 8000. CORS para el frontend Vite.

Al arrancar se precargan los modelos ML (globales). Los datos por empresa
se cargan de forma perezosa tras el login (tenant).
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.settings import CORS_ORIGINS
from src.interfaces.api.dependencies import get_modelo_loader
from src.interfaces.api.routers import router

logger = logging.getLogger("oilmine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()

    # Modelos ML (globales, compartidos por todos los tenants)
    logger.info("Precargando modelos ML…")
    try:
        get_modelo_loader().precargar()
        logger.info(f"Modelos cargados en {time.perf_counter() - t0:.2f}s")
    except Exception as e:
        logger.error(f"Error precargando modelos: {e}")

    logger.info(f"App lista en {time.perf_counter() - t0:.2f}s totales.")
    yield


app = FastAPI(
    title="OilMine Analytics API",
    description=(
        "Sistema predictivo de mantenimiento — Flota 794AC Quellaveco. "
        "Autenticación Google + datos aislados por empresa (dominio email)."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],  # dev: aceptamos cualquier origen
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
