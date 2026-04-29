"""Carga perezosa y cacheada de los modelos ML.

Los tres tipos de modelo (clasificador XGBoost, 12 regresores LightGBM,
estimador de horas) se cargan en memoria la primera vez que se piden y
se reutilizan para todas las peticiones.
"""
from __future__ import annotations

import json
import threading
from typing import Dict, List, Optional

import joblib

from src.infrastructure.settings import (
    CLASIFICADOR_PATH,
    ESTIMADOR_PATH,
    FEAT_COLS_PATH,
    VARIABLES_ANALITICAS,
    regresor_path,
)


class ModeloLoader:
    _instance: Optional["ModeloLoader"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._clasificador = None
                    obj._estimador = None
                    obj._regresores: Dict[str, object] = {}
                    obj._feat_cols: Optional[List[str]] = None
                    cls._instance = obj
        return cls._instance

    # ------------------------------------------------------------------
    # Accesores
    # ------------------------------------------------------------------
    @property
    def clasificador(self):
        if self._clasificador is None:
            self._clasificador = joblib.load(CLASIFICADOR_PATH)
        return self._clasificador

    @property
    def estimador_horas(self):
        if self._estimador is None:
            self._estimador = joblib.load(ESTIMADOR_PATH)
        return self._estimador

    @property
    def feat_cols(self) -> List[str]:
        if self._feat_cols is None:
            with open(FEAT_COLS_PATH, "r", encoding="utf-8") as f:
                self._feat_cols = json.load(f)
        return self._feat_cols

    def regresor(self, variable: str):
        if variable not in self._regresores:
            path = regresor_path(variable)
            if not path.exists():
                raise FileNotFoundError(f"Modelo regresor no encontrado: {path}")
            self._regresores[variable] = joblib.load(path)
        return self._regresores[variable]

    # ------------------------------------------------------------------
    def precargar(self) -> None:
        """Fuerza la carga de todos los modelos (útil en startup de FastAPI)."""
        _ = self.clasificador
        _ = self.estimador_horas
        _ = self.feat_cols
        for v in VARIABLES_ANALITICAS:
            try:
                self.regresor(v)
            except FileNotFoundError:
                # Ignoramos si alguna variable no tiene regresor entrenado
                pass

    def modelos_cargados(self) -> bool:
        return self._clasificador is not None and self._estimador is not None
