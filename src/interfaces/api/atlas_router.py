"""Contexto read-only para Atlas.

Atlas no inventa datos: consume estos endpoints para explicar resultados ya
calculados por el backend ML y solo escala a slices acotados cuando necesita
evidencia adicional.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.application import (
    ListarEquiposUseCase,
    ObtenerHistorialUseCase,
    ObtenerResumenFlotaUseCase,
    PredecirEquipoUseCase,
)
from src.infrastructure.settings import (
    HTC_CONFIANZA_MAX,
    HTC_CONFIANZA_MIN,
    MUESTRAS_MINIMAS_CONFIABLES,
    N_LAGS,
    ROLLING_WINDOWS,
    VARIABLES_ANALITICAS,
    VARIABLES_BAJA_CONFIANZA,
)
from src.interfaces.api import dependencies as deps
from src.interfaces.api.atlas_context import (
    feature_counts,
    filter_rows,
    history_rows,
    sem_driver,
    top_importance,
    variable_signals,
)
from src.interfaces.api.schemas import AtlasSliceRequest
from src.interfaces.api.user_context import UserContext

router = APIRouter(prefix="/atlas", tags=["atlas"])


@router.get("/model-context")
def atlas_model_context(
    _: UserContext = Depends(deps.require_auth),
    loader=Depends(deps.get_modelo_loader),
) -> dict[str, Any]:
    feat_cols = loader.feat_cols
    return {
        "algorithms": {
            "estado": "XGBoost classifier: NORMAL, PRECAUCION, CRITICO",
            "predicciones_t1": "12 LightGBM regressors, one per lab variable",
            "horas_hasta_critico": "LightGBM regressor",
        },
        "feature_engineering": {
            "total_features": len(feat_cols),
            "variables": VARIABLES_ANALITICAS,
            "n_lags": N_LAGS,
            "rolling_windows": ROLLING_WINDOWS,
            "groups": feature_counts(feat_cols),
            "anti_leakage": "Rolling/trend features use shift(1); current sample is not leaked.",
            "oil_cycle_rule": "If Hora_Producto drops, lag features crossing that oil cycle are invalidated.",
        },
        "business_rules": {
            "rojo": [
                "estado_modelo == CRITICO",
                "horas_actuales >= 400",
                "horas_hasta_critico <= 50",
            ],
            "amarillo": [
                "estado_modelo == PRECAUCION",
                "horas_actuales >= 300",
                "horas_hasta_critico <= 150",
            ],
        },
        "confidence": {
            "min_samples": MUESTRAS_MINIMAS_CONFIABLES,
            "hours_to_critical_reliable_range": [HTC_CONFIANZA_MIN, HTC_CONFIANZA_MAX],
            "low_confidence_variables": VARIABLES_BAJA_CONFIANZA,
            "shap": "No runtime SHAP artifact is versioned; do not cite SHAP as evidence.",
            "pca": "PCA is not part of the runtime pipeline.",
        },
        "feature_importance_proxy": {
            "classifier_top": top_importance(loader.clasificador, feat_cols),
            "hours_to_critical_top": top_importance(loader.estimador_horas, feat_cols),
            "note": "Native feature importance is a model proxy, not causality.",
        },
    }


@router.get("/dashboard-context")
def atlas_dashboard_context(
    uc: ObtenerResumenFlotaUseCase = Depends(deps.get_resumen_flota_uc),
) -> dict[str, Any]:
    summary = uc.execute()
    equipos = []
    for e in summary.equipos:
        risk = []
        if e.semaforo.value == "ROJO":
            risk.append("critico")
        if not e.historia_suficiente:
            risk.append("historia insuficiente")
        if not e.horas_htc_confiable:
            risk.append("horas hasta critico fuera de rango confiable")
        equipos.append(
            {
                "equipo": e.equipo,
                "semaforo": e.semaforo.value,
                "estado_modelo": e.estado_modelo.value,
                "horas_actuales": round(e.horas_actuales, 2),
                "horas_hasta_critico": e.horas_hasta_critico,
                "ultima_muestra_fecha": e.ultima_muestra_fecha.isoformat()
                if e.ultima_muestra_fecha
                else None,
                "total_muestras": e.total_muestras,
                "historia_suficiente": e.historia_suficiente,
                "horas_htc_confiable": e.horas_htc_confiable,
                "risk_notes": risk,
            }
        )
    return {
        "total_equipos": summary.total_equipos,
        "criticos": summary.criticos,
        "precaucion": summary.precaucion,
        "normales": summary.normales,
        "equipos": equipos,
    }


@router.get("/equipos/{equipo_id}/context")
def atlas_equipment_context(
    equipo_id: str,
    pred_uc: PredecirEquipoUseCase = Depends(deps.get_predecir_uc),
    hist_uc: ObtenerHistorialUseCase = Depends(deps.get_historial_uc),
) -> dict[str, Any]:
    try:
        pred = pred_uc.execute(equipo_id)
        equipo = hist_uc.execute(equipo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "equipo": pred.equipo,
        "prediction": {
            "semaforo": pred.semaforo.value,
            "estado_modelo": pred.estado_modelo.value,
            "horas_actuales": round(pred.horas_actuales, 2),
            "horas_hasta_critico": pred.horas_hasta_critico,
            "ultima_muestra_fecha": pred.ultima_muestra_fecha.isoformat()
            if pred.ultima_muestra_fecha
            else None,
            "historia_suficiente": pred.historia_suficiente,
            "horas_htc_confiable": pred.horas_htc_confiable,
            "advertencias": pred.advertencias,
            "drivers": sem_driver(pred),
        },
        "variables": variable_signals(pred, equipo),
        "recent_history": list(reversed(history_rows(equipo, VARIABLES_ANALITICAS)[-12:])),
    }


@router.post("/slices")
def atlas_slices(
    body: AtlasSliceRequest,
    list_uc: ListarEquiposUseCase = Depends(deps.get_listar_equipos_uc),
    hist_uc: ObtenerHistorialUseCase = Depends(deps.get_historial_uc),
) -> dict[str, Any]:
    variables = body.variables or VARIABLES_ANALITICAS
    invalid = [v for v in variables if v not in VARIABLES_ANALITICAS]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Variables invalidas: {invalid}")

    equipos = [body.equipo_id] if body.equipo_id else list_uc.execute()
    rows: list[dict[str, Any]] = []
    for equipo_id in equipos:
        try:
            equipo = hist_uc.execute(equipo_id)
        except ValueError:
            continue
        rows.extend(history_rows(equipo, variables))

    rows = filter_rows(rows, body.fecha_desde, body.fecha_hasta)
    rows.sort(key=lambda row: (row.get("equipo") or "", row.get("fecha") or "", row.get("hora_producto") or 0))
    limited = rows[-body.max_rows :]
    return {
        "row_count_total": len(rows),
        "row_count_returned": len(limited),
        "truncated": len(rows) > len(limited),
        "variables": variables,
        "rows": limited,
    }
