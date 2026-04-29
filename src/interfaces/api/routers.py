"""Routers FastAPI — consolida health, flota, equipos, muestras, exportar.

Un solo módulo para respetar la directiva "no crees carpetas que no sean
necesarias" sin sacrificar la separación por responsabilidades (cada router
es una función independiente con su propio prefix).
"""
from __future__ import annotations

import io
from datetime import date
from typing import Dict, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.application import (
    ListarEquiposUseCase,
    NuevaMuestraDTO,
    ObtenerHistorialUseCase,
    ObtenerResumenFlotaUseCase,
    PredecirEquipoUseCase,
    RegistrarMuestraUseCase,
)
from src.domain import EstadoEquipo, Prediccion
from src.infrastructure.settings import (
    LIMITES_ALERTA,
    VAR_TO_SLUG,
    VARIABLES_ANALITICAS,
    VARIABLES_BAJA_CONFIANZA,
)
from src.interfaces.api import dependencies as deps
from src.interfaces.api.schemas import (
    EquiposResponse,
    FlotaResumenResponse,
    HealthResponse,
    HistorialResponse,
    LimiteAlertaSchema,
    MuestraHistorial,
    NuevaMuestraRequest,
    PrediccionResponse,
    ResumenEquipoSchema,
    VariablesResponse,
)


# ======================================================================
# Helpers de mapeo dominio → schema
# ======================================================================
def _prediccion_to_schema(p: Prediccion) -> PrediccionResponse:
    return PrediccionResponse(
        equipo=p.equipo,
        semaforo=p.semaforo.value,
        estado_modelo=p.estado_modelo.value,
        horas_actuales=round(p.horas_actuales, 2),
        horas_hasta_critico=p.horas_hasta_critico,
        predicciones_t1=p.predicciones_t1,
        variables_baja_confianza=p.variables_baja_confianza,
        ultima_muestra_fecha=p.ultima_muestra_fecha,
        historia_suficiente=p.historia_suficiente,
        horas_htc_confiable=p.horas_htc_confiable,
        advertencias=p.advertencias,
    )


# ======================================================================
# Routers
# ======================================================================
router = APIRouter()


# ---------- Health --------------------------------------------------
@router.get("/health", response_model=HealthResponse, tags=["health"])
def health(loader=Depends(deps.get_modelo_loader)) -> HealthResponse:
    return HealthResponse(status="ok", modelos_cargados=loader.modelos_cargados())


# ---------- Metadata ------------------------------------------------
@router.get("/variables", response_model=VariablesResponse, tags=["metadata"])
def variables() -> VariablesResponse:
    limites = []
    for v in VARIABLES_ANALITICAS:
        cfg = LIMITES_ALERTA.get(v, {})
        limites.append(
            LimiteAlertaSchema(
                variable=v,
                direccion=cfg.get("direccion", "mayor"),
                verde_min=cfg.get("verde_min"),
                verde_max=cfg.get("verde_max"),
                amarillo_min=cfg.get("amarillo_min"),
                amarillo_max=cfg.get("amarillo_max"),
                rojo_min=cfg.get("rojo_min"),
                rojo_max=cfg.get("rojo_max"),
            )
        )
    return VariablesResponse(
        variables=VARIABLES_ANALITICAS,
        baja_confianza=VARIABLES_BAJA_CONFIANZA,
        limites=limites,
    )


# ---------- Equipos -------------------------------------------------
@router.get("/equipos", response_model=EquiposResponse, tags=["equipos"])
def listar_equipos(uc: ListarEquiposUseCase = Depends(deps.get_listar_equipos_uc)):
    return EquiposResponse(equipos=uc.execute())


@router.get(
    "/equipos/{equipo_id}/prediccion",
    response_model=PrediccionResponse,
    tags=["equipos"],
)
def prediccion_equipo(
    equipo_id: str,
    uc: PredecirEquipoUseCase = Depends(deps.get_predecir_uc),
):
    try:
        pred = uc.execute(equipo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _prediccion_to_schema(pred)


@router.get(
    "/equipos/{equipo_id}/historial",
    response_model=HistorialResponse,
    tags=["equipos"],
)
def historial_equipo(
    equipo_id: str,
    uc: ObtenerHistorialUseCase = Depends(deps.get_historial_uc),
):
    try:
        equipo = uc.execute(equipo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    historial = []
    for m in equipo.muestras:
        valores = {k: v for k, v in m.variables.items() if v == v}  # filtra NaN
        historial.append(
            MuestraHistorial(
                fecha=m.fecha,
                hora_producto=m.hora_producto,
                estado=m.estado.value if m.estado else None,
                valores=valores,
            )
        )
    # Ordenado: más reciente primero (por fecha, fallback a hora_producto)
    historial.sort(
        key=lambda h: (h.fecha or date.min, h.hora_producto),
        reverse=True,
    )
    return HistorialResponse(
        equipo=equipo.id,
        total_muestras=len(historial),
        historial=historial,
    )


# ---------- Flota ---------------------------------------------------
@router.get("/flota/resumen", response_model=FlotaResumenResponse, tags=["flota"])
def resumen_flota(
    uc: ObtenerResumenFlotaUseCase = Depends(deps.get_resumen_flota_uc),
):
    r = uc.execute()
    return FlotaResumenResponse(
        total_equipos=r.total_equipos,
        criticos=r.criticos,
        precaucion=r.precaucion,
        normales=r.normales,
        equipos=[
            ResumenEquipoSchema(
                equipo=e.equipo,
                semaforo=e.semaforo.value,
                estado_modelo=e.estado_modelo.value,
                horas_actuales=round(e.horas_actuales, 2),
                horas_hasta_critico=e.horas_hasta_critico,
                ultima_muestra_fecha=e.ultima_muestra_fecha,
                total_muestras=e.total_muestras,
                historia_suficiente=e.historia_suficiente,
                horas_htc_confiable=e.horas_htc_confiable,
            )
            for e in r.equipos
        ],
    )


# ---------- Muestras ------------------------------------------------
@router.post(
    "/equipos/{equipo_id}/muestras",
    response_model=PrediccionResponse,
    tags=["muestras"],
)
def registrar_muestra(
    equipo_id: str,
    body: NuevaMuestraRequest,
    uc: RegistrarMuestraUseCase = Depends(deps.get_registrar_muestra_uc),
):
    # El request puede venir con nombres de variable reales o en slug.
    valores_normalizados: Dict[str, float] = {}
    slug_to_var = {v: k for k, v in VAR_TO_SLUG.items()}
    for k, v in body.valores.items():
        if k in VARIABLES_ANALITICAS:
            valores_normalizados[k] = float(v)
        elif k in slug_to_var:
            valores_normalizados[slug_to_var[k]] = float(v)

    faltantes = [v for v in VARIABLES_ANALITICAS if v not in valores_normalizados]
    if faltantes:
        raise HTTPException(
            status_code=422,
            detail=f"Faltan valores para las variables: {faltantes}",
        )

    estado = None
    if body.estado:
        try:
            estado = EstadoEquipo(body.estado.upper())
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"Estado inválido: {body.estado}"
            )

    dto = NuevaMuestraDTO(
        fecha=body.fecha,
        hora_producto=body.hora_producto,
        valores=valores_normalizados,
        estado=estado,
    )
    try:
        pred = uc.execute(equipo_id, dto)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _prediccion_to_schema(pred)


# ---------- Exportar ------------------------------------------------
def _df_to_streaming(df: pd.DataFrame, filename_base: str, formato: str) -> StreamingResponse:
    """Devuelve el DataFrame como descarga en CSV o XLSX."""
    if formato == "csv":
        data = df.to_csv(index=False).encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(data),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.csv"'
            },
        )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="datos")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename_base}.xlsx"'
        },
    )


def _filtrar_muestras_por_fecha(muestras, fecha_desde, fecha_hasta):
    if not fecha_desde and not fecha_hasta:
        return muestras
    out = []
    for m in muestras:
        if m.fecha is None:
            continue
        if fecha_desde and m.fecha < fecha_desde:
            continue
        if fecha_hasta and m.fecha > fecha_hasta:
            continue
        out.append(m)
    return out


@router.get("/equipos/{equipo_id}/exportar", tags=["equipos"])
def exportar_historial(
    equipo_id: str,
    formato: str = Query("excel", pattern="^(excel|csv)$"),
    fecha_desde: Optional[date] = Query(None, description="Filtro inclusivo"),
    fecha_hasta: Optional[date] = Query(None, description="Filtro inclusivo"),
    uc: ObtenerHistorialUseCase = Depends(deps.get_historial_uc),
):
    try:
        equipo = uc.execute(equipo_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    muestras = _filtrar_muestras_por_fecha(equipo.muestras, fecha_desde, fecha_hasta)

    rows = []
    for m in muestras:
        row = {
            "Equipo": equipo.id,
            "Fecha": m.fecha,
            "Hora_Producto": m.hora_producto,
            "Estado": m.estado.value if m.estado else None,
        }
        row.update(m.variables)
        rows.append(row)
    df = pd.DataFrame(rows)

    # Sufijo con rango si aplica
    rango = ""
    if fecha_desde or fecha_hasta:
        rango = f"_{fecha_desde or 'inicio'}_a_{fecha_hasta or 'hoy'}"
    return _df_to_streaming(df, f"{equipo_id}_historial{rango}", formato)


@router.get("/flota/exportar", tags=["flota"])
def exportar_resumen_flota(
    formato: str = Query("excel", pattern="^(excel|csv)$"),
    uc: ObtenerResumenFlotaUseCase = Depends(deps.get_resumen_flota_uc),
):
    """Descarga el resumen actual de toda la flota (una fila por equipo)."""
    r = uc.execute()
    rows = []
    for e in r.equipos:
        rows.append({
            "Equipo": e.equipo,
            "Semáforo": e.semaforo.value,
            "Estado_modelo": e.estado_modelo.value,
            "Horas_actuales": round(e.horas_actuales, 2),
            "Horas_hasta_critico": e.horas_hasta_critico,
            "Última_muestra": e.ultima_muestra_fecha,
            "Total_muestras": e.total_muestras,
            "Historia_suficiente": e.historia_suficiente,
            "Horas_HTC_confiable": e.horas_htc_confiable,
        })
    df = pd.DataFrame(rows)
    hoy = date.today().isoformat()
    return _df_to_streaming(df, f"flota_resumen_{hoy}", formato)
