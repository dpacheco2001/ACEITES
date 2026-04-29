"""Ingeniería de features — réplica fiel del notebook de entrenamiento.

Los nombres truncados (var[:18], var[:15]) y la lógica de invalidación por
ciclo de aceite son IDÉNTICOS al código de `fase2_motor_predictivo_794AC.ipynb`.
Un error aquí produce predicciones silenciosamente incorrectas.
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

from src.domain import Equipo, Muestra
from src.infrastructure.settings import (
    ESTADO_MAP,
    N_LAGS,
    ROLLING_WINDOWS,
    VARIABLES_ANALITICAS,
)


def _lin_slope(x: pd.Series) -> float:
    vals = x.dropna()
    if len(vals) < 2:
        return np.nan
    xi = np.arange(len(vals))
    return float(np.polyfit(xi, vals.values, 1)[0])


def equipo_a_dataframe(equipo: Equipo) -> pd.DataFrame:
    """Convierte el agregado `Equipo` a un DataFrame con las columnas originales."""
    rows = []
    for m in equipo.muestras:
        row = {
            "Equipo": equipo.id,
            "Fecha": pd.to_datetime(m.fecha) if m.fecha else pd.NaT,
            "Hora_Producto": m.hora_producto,
            "Estado": m.estado.value if m.estado else None,
        }
        for v in VARIABLES_ANALITICAS:
            row[v] = m.variables.get(v, np.nan)
        rows.append(row)
    df = pd.DataFrame(rows)
    df["Estado_num"] = df["Estado"].map(ESTADO_MAP)
    return df


def build_feature_row(equipo: Equipo, feat_cols: List[str]) -> pd.DataFrame:
    """Construye UNA fila de features alineada al `feat_cols` del entrenamiento.

    La fila representa el estado del equipo en su última muestra y es lo que
    alimenta a los modelos clasificador/regresores/estimador para hacer
    predicciones sobre t+1.
    """
    grp = equipo_a_dataframe(equipo)
    if grp.empty:
        raise ValueError(f"Equipo {equipo.id} no tiene muestras")

    # Las muestras llegan del repositorio en orden cronológico (Fecha,
    # Hora_Producto). Mantenemos ese orden para que la "última" muestra
    # sea la más reciente por fecha — semánticamente correcto para
    # mantenimiento predictivo en tiempo real.
    grp = grp.reset_index(drop=True)

    # Ciclos de aceite: hora_actual < hora_anterior ⇒ cambio de aceite
    delta_hora = grp["Hora_Producto"].diff()
    cambio_aceite = (delta_hora < 0)
    ciclo_id = cambio_aceite.cumsum()

    feat = pd.DataFrame(index=grp.index)

    for var in VARIABLES_ANALITICAS:
        if var not in grp.columns:
            continue
        s = grp[var]

        # LAGS (k = 1..N_LAGS) — invalidar si cruza un cambio de aceite
        for k in range(1, N_LAGS + 1):
            col = f"lag{k}_{var[:18]}"
            feat[col] = s.shift(k)
            ciclo_shifted = ciclo_id.shift(k)
            feat.loc[ciclo_id != ciclo_shifted, col] = np.nan

        # DELTAS (k = 1..N_LAGS-1)
        for k in range(1, N_LAGS):
            col = f"delta{k}_{var[:18]}"
            feat[col] = s.shift(k) - s.shift(k + 1)
            ciclo_k1 = ciclo_id.shift(k + 1)
            feat.loc[ciclo_id != ciclo_k1, col] = np.nan

        # ROLLING — anti-leakage: rolling sobre shift(1)
        s_shifted = s.shift(1)
        for w in ROLLING_WINDOWS:
            feat[f"rollmean{w}_{var[:15]}"] = (
                s_shifted.rolling(w, min_periods=2).mean()
            )
            feat[f"rollstd{w}_{var[:15]}"] = (
                s_shifted.rolling(w, min_periods=2).std()
            )

        # TREND slope sobre ventana rolling de 3
        feat[f"trend_{var[:18]}"] = (
            s_shifted.rolling(3, min_periods=2).apply(_lin_slope, raw=False)
        )

    # Features adicionales
    feat["horas_actuales"] = grp["Hora_Producto"]
    feat["horas_desde_ultima"] = delta_hora
    feat["es_cambio_aceite"] = cambio_aceite.astype(int)
    feat["estado_lag1"] = grp["Estado_num"].shift(1)
    feat["estado_lag2"] = grp["Estado_num"].shift(2)

    # Tomamos SOLO la última fila (estado "actual" del equipo para predecir t+1)
    last = feat.iloc[[-1]]

    # Alinear con el orden/conjunto exacto de feat_cols del entrenamiento.
    # Si falta alguna columna, rellenamos con 0.0 (comportamiento coincidente
    # con el fallback descrito en la guía).
    data = {
        col: last[col].values if col in last.columns else np.array([np.nan])
        for col in feat_cols
    }
    aligned = pd.DataFrame(data, index=last.index).fillna(0.0)
    return aligned
