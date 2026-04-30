"""Helpers de contexto para endpoints Atlas."""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from src.domain import Equipo, Prediccion
from src.infrastructure.settings import LIMITES_ALERTA, VARIABLES_ANALITICAS


def round_value(value: Any, ndigits: int = 4) -> Any:
    if isinstance(value, float):
        return round(value, ndigits)
    return value


def limit_status(variable: str, value: float | None) -> str:
    if value is None:
        return "SIN_DATO"
    cfg = LIMITES_ALERTA.get(variable, {})
    direction = cfg.get("direccion")
    if direction == "menor":
        if cfg.get("rojo_max") is not None and value < cfg["rojo_max"]:
            return "ROJO"
        if cfg.get("amarillo_min") is not None and value < cfg["amarillo_max"]:
            return "AMARILLO"
        return "VERDE"
    if direction == "rango":
        if cfg.get("rojo_max") is not None and value < cfg["rojo_max"]:
            return "ROJO"
        if cfg.get("rojo_min") is not None and value > cfg["rojo_min"]:
            return "ROJO"
        if cfg.get("amarillo_min") is not None and value < cfg["amarillo_min"]:
            return "AMARILLO"
        if cfg.get("amarillo_max") is not None and value > cfg["amarillo_max"]:
            return "AMARILLO"
        return "VERDE"
    if cfg.get("rojo_min") is not None and value > cfg["rojo_min"]:
        return "ROJO"
    if cfg.get("amarillo_max") is not None and value > cfg["amarillo_max"]:
        return "AMARILLO"
    return "VERDE"


def sem_driver(pred: Prediccion) -> list[str]:
    drivers = []
    if pred.estado_modelo.value == "CRITICO":
        drivers.append("El clasificador XGBoost predice CRITICO.")
    elif pred.estado_modelo.value == "PRECAUCION":
        drivers.append("El clasificador XGBoost predice PRECAUCION.")
    if pred.horas_actuales >= 400:
        drivers.append("Horas actuales de aceite >= 400h.")
    elif pred.horas_actuales >= 300:
        drivers.append("Horas actuales de aceite >= 300h.")
    if pred.horas_hasta_critico is not None:
        if pred.horas_hasta_critico <= 50:
            drivers.append("Horas hasta critico <= 50h.")
        elif pred.horas_hasta_critico <= 150:
            drivers.append("Horas hasta critico <= 150h.")
    return drivers or ["No hay disparadores de riesgo; semaforo en rango normal."]


def latest_values(equipo: Equipo) -> dict[str, float | None]:
    ultima = equipo.ultima_muestra
    if not ultima:
        return {}
    return {
        var: round_value(ultima.variables.get(var))
        for var in VARIABLES_ANALITICAS
        if var in ultima.variables
    }


def variable_signals(pred: Prediccion, equipo: Equipo) -> list[dict[str, Any]]:
    current = latest_values(equipo)
    signals = []
    for var in VARIABLES_ANALITICAS:
        now = current.get(var)
        nxt = pred.predicciones_t1.get(var)
        delta = None if now is None or nxt is None else round(nxt - now, 4)
        signals.append(
            {
                "variable": var,
                "actual": now,
                "prediccion_t1": nxt,
                "delta_t1": delta,
                "limite_actual": limit_status(var, now),
                "limite_t1": limit_status(var, nxt),
                "baja_confianza": var in pred.variables_baja_confianza,
            }
        )
    return signals


def feature_counts(feat_cols: list[str]) -> dict[str, int]:
    prefixes = Counter()
    for col in feat_cols:
        prefix = col.split("_", 1)[0]
        if prefix.startswith("rollmean"):
            prefix = "rollmean"
        elif prefix.startswith("rollstd"):
            prefix = "rollstd"
        prefixes[prefix] += 1
    return dict(prefixes)


def top_importance(model: Any, feat_cols: list[str], limit: int = 15) -> list[dict[str, Any]]:
    values = getattr(model, "feature_importances_", None)
    if values is None:
        return []
    pairs = [
        {"feature": name, "importance": float(score)}
        for name, score in zip(feat_cols, values)
    ]
    pairs.sort(key=lambda item: item["importance"], reverse=True)
    return pairs[:limit]


def history_rows(equipo: Equipo, variables: list[str]) -> list[dict[str, Any]]:
    rows = []
    for muestra in equipo.muestras:
        row = {
            "equipo": equipo.id,
            "fecha": muestra.fecha.isoformat() if muestra.fecha else None,
            "hora_producto": muestra.hora_producto,
            "estado": muestra.estado.value if muestra.estado else None,
        }
        for var in variables:
            row[var] = round_value(muestra.variables.get(var))
        rows.append(row)
    return rows


def filter_rows(
    rows: list[dict[str, Any]],
    fecha_desde: date | None,
    fecha_hasta: date | None,
) -> list[dict[str, Any]]:
    filtered = []
    for row in rows:
        raw_fecha = row.get("fecha")
        row_date = date.fromisoformat(raw_fecha) if raw_fecha else None
        if fecha_desde and (row_date is None or row_date < fecha_desde):
            continue
        if fecha_hasta and (row_date is None or row_date > fecha_hasta):
            continue
        filtered.append(row)
    return filtered
