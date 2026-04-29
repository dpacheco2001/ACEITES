"""Inyección de dependencias — ensambla la composición raíz de la app.

Los use-cases costosos (predicción por equipo, resumen de flota, registrar
muestra) se envuelven con decoradores de cache TTL para que el frontend
perciba latencia de ms en vez de segundos.
"""
from __future__ import annotations

from functools import lru_cache

from src.application import (
    IEquipoRepository,
    IMuestraRepository,
    IPredictor,
    ListarEquiposUseCase,
    ObtenerHistorialUseCase,
    ObtenerResumenFlotaUseCase,
    PredecirEquipoUseCase,
    RegistrarMuestraUseCase,
)
from src.domain import SemaforoService
from src.infrastructure.cache import TTLCache
from src.infrastructure.cached_usecases import (
    CachedObtenerResumenFlotaUseCase,
    CachedPredecirEquipoUseCase,
    CachedRegistrarMuestraUseCase,
)
from src.infrastructure.excel_repository import (
    ExcelEquipoRepository,
    ExcelManager,
    ExcelMuestraRepository,
)
from src.infrastructure.modelo_loader import ModeloLoader
from src.infrastructure.predictor import PredictorAdapter
from src.infrastructure.settings import PREDICCION_CACHE_TTL


# ----------------------------------------------------------------------
# Singletons básicos
# ----------------------------------------------------------------------
@lru_cache
def get_excel_manager() -> ExcelManager:
    return ExcelManager()


@lru_cache
def get_modelo_loader() -> ModeloLoader:
    return ModeloLoader()


@lru_cache
def get_semaforo_service() -> SemaforoService:
    return SemaforoService()


@lru_cache
def get_equipo_repository() -> IEquipoRepository:
    return ExcelEquipoRepository(get_excel_manager())


@lru_cache
def get_muestra_repository() -> IMuestraRepository:
    return ExcelMuestraRepository(get_excel_manager())


@lru_cache
def get_predictor() -> IPredictor:
    return PredictorAdapter(get_modelo_loader(), get_semaforo_service())


# ----------------------------------------------------------------------
# Cache compartido — una sola instancia para que flota+equipo invaliden entre sí
# ----------------------------------------------------------------------
@lru_cache
def get_prediction_cache() -> TTLCache:
    return TTLCache(ttl_seconds=PREDICCION_CACHE_TTL)


# ----------------------------------------------------------------------
# Casos de uso
# ----------------------------------------------------------------------
@lru_cache
def get_listar_equipos_uc() -> ListarEquiposUseCase:
    return ListarEquiposUseCase(get_equipo_repository())


@lru_cache
def get_historial_uc() -> ObtenerHistorialUseCase:
    return ObtenerHistorialUseCase(get_equipo_repository())


@lru_cache
def get_predecir_uc() -> CachedPredecirEquipoUseCase:
    """Versión cacheada del predictor por equipo."""
    inner = PredecirEquipoUseCase(get_equipo_repository(), get_predictor())
    return CachedPredecirEquipoUseCase(inner, get_prediction_cache())


@lru_cache
def get_resumen_flota_uc() -> CachedObtenerResumenFlotaUseCase:
    """Versión cacheada del resumen de flota (la más costosa)."""
    inner = ObtenerResumenFlotaUseCase(get_equipo_repository(), get_predictor())
    return CachedObtenerResumenFlotaUseCase(inner, get_prediction_cache())


@lru_cache
def get_registrar_muestra_uc() -> CachedRegistrarMuestraUseCase:
    """Versión que invalida el cache tras registrar una muestra."""
    inner = RegistrarMuestraUseCase(
        get_equipo_repository(),
        get_muestra_repository(),
        get_predictor(),
    )
    return CachedRegistrarMuestraUseCase(inner, get_prediction_cache())
