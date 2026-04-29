"""Cache TTL thread-safe — evita recomputar predicciones ML por cada request.

Uso típico:

    cache = TTLCache(ttl_seconds=300)          # 5 min
    cache.get_or_compute("flota_resumen", fn)  # fn() sólo si expiró o no existe
    cache.invalidate("flota_resumen")          # tras un POST de muestra

La idea: /flota/resumen dispara 33 predicciones (XGBoost + 12 LightGBM + HTC)
en cada llamada. En 5 minutos la respuesta no cambia a menos que alguien
registre una muestra nueva — de ahí el TTL + invalidación explícita.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple


class TTLCache:
    """Cache en memoria con TTL por entrada e invalidación explícita.

    Sin persistencia: se reinicia al reiniciar la app (es intencional, los
    modelos pueden haber cambiado).
    """

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self.ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    def get(self, key: str) -> Optional[Any]:
        """Devuelve el valor cacheado o None si expiró/no existe."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.monotonic() - ts > self.ttl:
                # Expirado: lo quitamos de una vez.
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), value)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Borra todas las entradas cuya key empiece con `prefix`."""
        with self._lock:
            doomed = [k for k in self._store if k.startswith(prefix)]
            for k in doomed:
                self._store.pop(k, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    # ------------------------------------------------------------------
    def get_or_compute(self, key: str, compute: Callable[[], Any]) -> Any:
        """Devuelve el valor cacheado o lo calcula con `compute()` y lo guarda.

        Nota: `compute` corre fuera del lock para no bloquear a otros requests
        durante una predicción costosa. Esto admite "stampede" (dos requests
        calculando lo mismo a la vez) pero es aceptable acá: el cache se
        auto-sana en la segunda escritura y los modelos son idempotentes.
        """
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute()
        self.set(key, value)
        return value

    # ------------------------------------------------------------------
    # Para debug / /health
    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "entries": len(self._store),
                "keys": sorted(self._store.keys()),
                "ttl_seconds": self.ttl,
            }
