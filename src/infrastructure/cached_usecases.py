"""Decoradores de casos de uso con cache TTL.

Respetan la misma interfaz pública (`.execute(...)`) para que el resto del
código (routers, DI) no note la diferencia. La invalidación vive acá para
mantener a los use-cases puros.

Keys usados:
  - ``flota_resumen``          → resultado de /flota/resumen
  - ``prediccion:{equipo_id}`` → resultado de /equipos/{id}/prediccion
"""
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


def _pred_key(equipo_id: str) -> str:
    return f"{PREDICCION_PREFIX}{equipo_id}"


# ======================================================================
# Predicción individual
# ======================================================================
class CachedPredecirEquipoUseCase:
    """Cachea el resultado de la predicción por equipo."""

    def __init__(
        self,
        inner: PredecirEquipoUseCase,
        cache: "TTLCache",
    ) -> None:
        self._inner = inner
        self._cache = cache

    def execute(self, equipo_id: str) -> "Prediccion":
        return self._cache.get_or_compute(
            _pred_key(equipo_id),
            lambda: self._inner.execute(equipo_id),
        )


# ======================================================================
# Resumen de flota
# ======================================================================
class CachedObtenerResumenFlotaUseCase:
    """Cachea /flota/resumen — el endpoint más caro (33 predicciones)."""

    def __init__(
        self,
        inner: ObtenerResumenFlotaUseCase,
        cache: "TTLCache",
    ) -> None:
        self._inner = inner
        self._cache = cache

    def execute(self) -> "ResumenFlota":
        return self._cache.get_or_compute(FLOTA_KEY, self._inner.execute)

    def warm_up(self) -> None:
        """Pre-computa el resumen y lo deja en cache. Se llama al arranque."""
        self._cache.invalidate(FLOTA_KEY)  # forzar recompute fresco
        self.execute()


# ======================================================================
# Registrar muestra — invalida y repuebla
# ======================================================================
class CachedRegistrarMuestraUseCase:
    """Al registrar una muestra nueva, el cache del equipo y el de la flota
    quedan obsoletos. Los invalidamos sincrónicamente para que la siguiente
    lectura vea datos consistentes.
    """

    def __init__(
        self,
        inner: RegistrarMuestraUseCase,
        cache: "TTLCache",
    ) -> None:
        self._inner = inner
        self._cache = cache

    def execute(self, equipo_id: str, nueva: NuevaMuestraDTO) -> "Prediccion":
        pred = self._inner.execute(equipo_id, nueva)
        # Invalida el equipo afectado y la flota completa.
        self._cache.invalidate(_pred_key(equipo_id))
        self._cache.invalidate(FLOTA_KEY)
        # Re-siembra la predicción del equipo (usa la respuesta que ya tenemos
        # para no pagar el costo otra vez).
        self._cache.set(_pred_key(equipo_id), pred)
        return pred
