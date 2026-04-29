"""Adaptador de predicción — une feature_builder + modelos ML.

Implementa el puerto `IPredictor` de la capa de aplicación.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.application import IPredictor
from src.domain import (
    Equipo,
    EstadoEquipo,
    Prediccion,
    SemaforoService,
)
from src.infrastructure.feature_builder import build_feature_row
from src.infrastructure.modelo_loader import ModeloLoader
from src.infrastructure.settings import (
    ESTADO_INV,
    HTC_CONFIANZA_MAX,
    HTC_CONFIANZA_MIN,
    MUESTRAS_MINIMAS_CONFIABLES,
    VARIABLES_ANALITICAS,
    VARIABLES_BAJA_CONFIANZA,
)


class PredictorAdapter(IPredictor):
    def __init__(
        self,
        loader: ModeloLoader,
        semaforo_service: SemaforoService,
    ) -> None:
        self.loader = loader
        self.semaforo_service = semaforo_service

    def predecir(self, equipo: Equipo) -> Prediccion:
        if not equipo.muestras:
            raise ValueError(f"Equipo {equipo.id} sin muestras")

        feat_cols = self.loader.feat_cols
        X = build_feature_row(equipo, feat_cols)

        # ------------------------------------------------------------------
        # Modelo A — clasificador de estado (XGBoost, input numpy array)
        # ------------------------------------------------------------------
        clf = self.loader.clasificador
        y_pred = int(clf.predict(X.values)[0])
        estado_modelo = EstadoEquipo(ESTADO_INV.get(y_pred, "CRITICO"))

        # ------------------------------------------------------------------
        # Modelo B — regresores por variable (LightGBM, admite DataFrame)
        # ------------------------------------------------------------------
        predicciones_t1 = {}
        for var in VARIABLES_ANALITICAS:
            try:
                reg = self.loader.regresor(var)
            except FileNotFoundError:
                continue
            # LightGBM acepta DataFrame (auto-matchea feature names normalizados)
            pred = float(reg.predict(X)[0])
            predicciones_t1[var] = round(pred, 4)

        # ------------------------------------------------------------------
        # Modelo C — horas hasta estado CRITICO
        # ------------------------------------------------------------------
        horas_hasta_critico = None
        try:
            horas_pred = float(self.loader.estimador_horas.predict(X)[0])
            horas_hasta_critico = max(0.0, round(horas_pred, 2))
        except Exception:
            horas_hasta_critico = None

        # ------------------------------------------------------------------
        # Valores actuales del equipo
        # ------------------------------------------------------------------
        ultima = equipo.muestras[-1]
        horas_actuales = ultima.hora_producto

        # ------------------------------------------------------------------
        # Semáforo (regla de negocio del dominio)
        # ------------------------------------------------------------------
        semaforo = self.semaforo_service.calcular(
            estado_modelo=estado_modelo,
            horas_actuales=horas_actuales,
            horas_hasta_critico=horas_hasta_critico,
        )

        # ------------------------------------------------------------------
        # Flags de confianza + advertencias
        # ------------------------------------------------------------------
        historia_suficiente = len(equipo.muestras) >= MUESTRAS_MINIMAS_CONFIABLES
        horas_htc_confiable = (
            horas_hasta_critico is not None
            and HTC_CONFIANZA_MIN <= horas_hasta_critico <= HTC_CONFIANZA_MAX
        )
        advertencias: list[str] = []
        if not historia_suficiente:
            advertencias.append(
                f"Historia insuficiente ({len(equipo.muestras)} muestras, "
                f"se recomiendan ≥{MUESTRAS_MINIMAS_CONFIABLES}). "
                f"Predicciones con baja confianza."
            )
        if horas_hasta_critico is not None and not horas_htc_confiable:
            advertencias.append(
                f"Horas hasta crítico fuera del rango confiable del Modelo C "
                f"({HTC_CONFIANZA_MIN:.0f}-{HTC_CONFIANZA_MAX:.0f}h). "
                f"Valor: {horas_hasta_critico:.1f}h — interpretar con cautela."
            )

        return Prediccion(
            equipo=equipo.id,
            semaforo=semaforo,
            estado_modelo=estado_modelo,
            horas_actuales=horas_actuales,
            horas_hasta_critico=horas_hasta_critico,
            predicciones_t1=predicciones_t1,
            variables_baja_confianza=[
                v for v in VARIABLES_BAJA_CONFIANZA if v in predicciones_t1
            ],
            ultima_muestra_fecha=ultima.fecha,
            historia_suficiente=historia_suficiente,
            horas_htc_confiable=horas_htc_confiable,
            advertencias=advertencias,
        )
