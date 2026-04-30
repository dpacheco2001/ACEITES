"""Inyección de dependencias — casos de uso por tenant y cache namespaced."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

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
from src.interfaces.api.auth_dependencies import (
    require_admin,
    require_auth,
)
from src.infrastructure.cache import TTLCache
from src.infrastructure.cached_usecases import (
    CachedObtenerResumenFlotaUseCase,
    CachedPredecirEquipoUseCase,
    CachedRegistrarMuestraUseCase,
)
from src.infrastructure.excel_repository import ExcelEquipoRepository, ExcelMuestraRepository
from src.infrastructure.modelo_loader import ModeloLoader
from src.infrastructure.predictor import PredictorAdapter
from src.infrastructure.settings import PREDICCION_CACHE_TTL
from src.infrastructure.tenant_excel_registry import TenantExcelRegistry
from src.interfaces.api.user_context import UserContext


# ------------------------------------------------------------------
# Re-export para routers
# ------------------------------------------------------------------
__all__ = [
    "get_prediction_cache",
    "get_modelo_loader",
    "require_auth",
    "require_admin",
    "get_listar_equipos_uc",
    "get_historial_uc",
    "get_predecir_uc",
    "get_resumen_flota_uc",
    "get_registrar_muestra_uc",
]


def _repos_for(uc: UserContext) -> tuple[IEquipoRepository, IMuestraRepository]:
    mgr = TenantExcelRegistry.get_manager(uc.tenant_key)
    return ExcelEquipoRepository(mgr), ExcelMuestraRepository(mgr)


@lru_cache
def get_modelo_loader() -> ModeloLoader:
    return ModeloLoader()


@lru_cache
def get_semaforo_service() -> SemaforoService:
    return SemaforoService()


@lru_cache
def get_predictor() -> IPredictor:
    return PredictorAdapter(get_modelo_loader(), get_semaforo_service())


@lru_cache
def get_prediction_cache() -> TTLCache:
    return TTLCache(ttl_seconds=PREDICCION_CACHE_TTL)


def get_listar_equipos_uc(
    uc: UserContext = Depends(require_auth),
) -> ListarEquiposUseCase:
    eq_repo, _ = _repos_for(uc)
    return ListarEquiposUseCase(eq_repo)


def get_historial_uc(
    uc: UserContext = Depends(require_auth),
) -> ObtenerHistorialUseCase:
    eq_repo, _ = _repos_for(uc)
    return ObtenerHistorialUseCase(eq_repo)


def get_predecir_uc(
    uc: UserContext = Depends(require_auth),
) -> CachedPredecirEquipoUseCase:
    eq_repo, _ = _repos_for(uc)
    inner = PredecirEquipoUseCase(eq_repo, get_predictor())
    return CachedPredecirEquipoUseCase(
        inner, get_prediction_cache(), uc.tenant_key
    )


def get_resumen_flota_uc(
    uc: UserContext = Depends(require_auth),
) -> CachedObtenerResumenFlotaUseCase:
    eq_repo, _ = _repos_for(uc)
    inner = ObtenerResumenFlotaUseCase(eq_repo, get_predictor())
    return CachedObtenerResumenFlotaUseCase(
        inner, get_prediction_cache(), uc.tenant_key
    )


def get_registrar_muestra_uc(
    uc: UserContext = Depends(require_auth),
) -> CachedRegistrarMuestraUseCase:
    eq_repo, muestra_repo = _repos_for(uc)
    inner = RegistrarMuestraUseCase(
        eq_repo,
        muestra_repo,
        get_predictor(),
    )
    return CachedRegistrarMuestraUseCase(
        inner, get_prediction_cache(), uc.tenant_key
    )
