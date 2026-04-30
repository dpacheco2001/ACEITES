"""Decoradores de casos de uso con cache TTL por tenant."""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.application import (
    NuevaMuestraDTO,
    ObtenerResumenFlotaUseCase,
    PredecirEquipoUseCase,
    RegistrarMuestraUseCase,
)

if TYPE_CHECKING:
    from src.domain import Prediccion
    from src.application import ResumenFlota
    from src.infrastructure.cache import TTLCache


FLOTA_KEY = "flota_resumen"
PREDICCION_PREFIX = "prediccion:"


def _cache_namespace(tenant_key: str) -> str:
    return f"t:{tenant_key}:"


def _pred_key(equipo_id: str) -> str:
    return f"{PREDICCION_PREFIX}{equipo_id}"


class CachedPredecirEquipoUseCase:
    """Cachea predicción por equipo y tenant."""

    def __init__(
        self,
        inner: PredecirEquipoUseCase,
        cache: "TTLCache",
        tenant_key: str,
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._pfx = _cache_namespace(tenant_key)

    def execute(self, equipo_id: str) -> "Prediccion":
        key = f"{self._pfx}{_pred_key(equipo_id)}"
        return self._cache.get_or_compute(
            key,
            lambda: self._inner.execute(equipo_id),
        )


class CachedObtenerResumenFlotaUseCase:
    """Cachea /flota/resumen por tenant."""

    def __init__(
        self,
        inner: ObtenerResumenFlotaUseCase,
        cache: "TTLCache",
        tenant_key: str,
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._flota_key = f"{_cache_namespace(tenant_key)}{FLOTA_KEY}"

    def execute(self) -> "ResumenFlota":
        return self._cache.get_or_compute(self._flota_key, self._inner.execute)

    def warm_up(self) -> None:
        self._cache.invalidate(self._flota_key)
        self.execute()


class CachedRegistrarMuestraUseCase:
    """Registrar muestra: invalidación cache scoped al tenant."""

    def __init__(
        self,
        inner: RegistrarMuestraUseCase,
        cache: "TTLCache",
        tenant_key: str,
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._pfx = _cache_namespace(tenant_key)

    def execute(self, equipo_id: str, nueva: NuevaMuestraDTO) -> "Prediccion":
        pred = self._inner.execute(equipo_id, nueva)
        self._cache.invalidate(f"{self._pfx}{_pred_key(equipo_id)}")
        self._cache.invalidate(f"{self._pfx}{FLOTA_KEY}")
        self._cache.set(f"{self._pfx}{_pred_key(equipo_id)}", pred)
        return pred
