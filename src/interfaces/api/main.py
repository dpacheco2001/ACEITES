"""OilMine Analytics: FastAPI app principal.

Al arrancar se precargan los modelos ML globales. Los datos por tenant se
cargan de forma perezosa tras el login porque dependen del tenant.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.settings import CORS_ORIGINS
from src.interfaces.api.admin_router import router as admin_router
from src.interfaces.api.atlas_router import router as atlas_router
from src.interfaces.api.auth_router import router as auth_router
from src.interfaces.api.dataset_router import router as dataset_router
from src.interfaces.api.dependencies import get_modelo_loader
from src.interfaces.api.owner_router import router as owner_router
from src.interfaces.api.routers import router as api_router

logger = logging.getLogger("oilmine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()

    logger.info("Precargando modelos ML...")
    try:
        get_modelo_loader().precargar()
        logger.info("Modelos cargados en %.2fs", time.perf_counter() - t0)
    except Exception as e:
        logger.error("Error precargando modelos: %s", e)

    logger.info("App lista en %.2fs totales.", time.perf_counter() - t0)
    yield


app = FastAPI(
    title="OilMine Analytics API",
    description=(
        "Sistema predictivo de mantenimiento. Autenticación Google y datos "
        "aislados por tenant."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)
app.include_router(atlas_router)
app.include_router(admin_router)
app.include_router(dataset_router)
app.include_router(owner_router)


@app.get("/", tags=["health"])
def root():
    return {
        "name": "OilMine Analytics",
        "docs": "/docs",
        "health": "/health",
    }
