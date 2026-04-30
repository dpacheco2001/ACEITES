"""Routers FastAPI — health público, auth, API protegida y admin."""
from __future__ import annotations

import io
from datetime import date
from typing import Dict, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from src.infrastructure.auth_db import get_auth_db
from src.infrastructure.google_id_token import verify_google_id_token
from src.infrastructure.jwt_session import create_access_token
from src.infrastructure.settings import GOOGLE_CLIENT_ID, LIMITES_ALERTA, VAR_TO_SLUG, VARIABLES_ANALITICAS, VARIABLES_BAJA_CONFIANZA
from src.infrastructure.tenant_excel_registry import TenantExcelRegistry
from src.interfaces.api import dependencies as deps
from src.interfaces.api.schemas import (
    AdminRolePatch,
    AdminUserItem,
    AdminUsersResponse,
    AuthResponse,
    EquiposResponse,
    FlotaResumenResponse,
    GoogleAuthRequest,
    GoogleClientConfigResponse,
    HealthResponse,
    HistorialResponse,
    LimiteAlertaSchema,
    MeResponse,
    MuestraHistorial,
    NuevaMuestraRequest,
    PrediccionResponse,
    ResumenEquipoSchema,
    UserPublic,
    VariablesResponse,
)
from src.interfaces.api.user_context import UserContext


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


def _user_public_from_row(u) -> UserPublic:
    db = get_auth_db()
    org = db.get_org_by_id(u.org_id)
    tenant = org.tenant_key if org else ""
    return UserPublic(
        id=u.id,
        email=u.email,
        org_id=u.org_id,
        tenant_key=tenant,
        role=u.role,
    )


# ======================================================================
# Routers
# ======================================================================
router = APIRouter()

# Autenticación: cada endpoint depende de casos de uso que inyectan `require_auth`.
protected = APIRouter()

auth_router = APIRouter(prefix="/auth", tags=["auth"])

admin_router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Health (público) -----------------------------------------
@router.get("/health", response_model=HealthResponse, tags=["health"])
def health(loader=Depends(deps.get_modelo_loader)) -> HealthResponse:
    return HealthResponse(status="ok", modelos_cargados=loader.modelos_cargados())


# ---------- Auth (público) -------------------------------------------
@auth_router.get("/client-config", response_model=GoogleClientConfigResponse)
def auth_client_config() -> GoogleClientConfigResponse:
    """Expone el Client ID configurado en el servidor para que el login no requiera .env en Vite."""
    return GoogleClientConfigResponse(google_client_id=GOOGLE_CLIENT_ID or "")


@auth_router.post("/google", response_model=AuthResponse)
def auth_google(body: GoogleAuthRequest) -> AuthResponse:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_CLIENT_ID no configurado en el servidor",
        )
    try:
        info = verify_google_id_token(body.id_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token de Google inválido: {e}") from e

    email_raw = info.get("email") or ""
    if not isinstance(email_raw, str) or "@" not in email_raw:
        raise HTTPException(status_code=400, detail="Google no devolvió email válido")
    if not info.get("email_verified"):
        raise HTTPException(status_code=400, detail="El correo de Google debe estar verificado")

    tenant_key = email_raw.split("@", 1)[1].strip().lower()
    google_sub = str(info["sub"])

    db = get_auth_db()
    existing = db.get_user_by_sub(google_sub)
    if existing:
        org = db.get_org_by_id(existing.org_id)
        if org is None:
            raise HTTPException(status_code=500, detail="Inconsistencia de organización")
        TenantExcelRegistry.ensure_tenant_dataset(org.tenant_key)
        TenantExcelRegistry.preload_tenant(org.tenant_key)

        tok = create_access_token(
            user_id=existing.id,
            org_id=existing.org_id,
            tenant_key=org.tenant_key,
            email=existing.email,
            role=existing.role,
            google_sub=existing.google_sub,
        )
        return AuthResponse(access_token=tok, user=_user_public_from_row(existing))

    org = db.get_org_by_tenant(tenant_key)
    if org is None:
        org = db.create_org(tenant_key)

    n_before = db.count_users_in_org(org.id)
    role = "ADMIN" if n_before == 0 else "CLIENTE"

    created = db.create_user(google_sub=google_sub, email=email_raw, org_id=org.id, role=role)
    TenantExcelRegistry.ensure_tenant_dataset(org.tenant_key)
    TenantExcelRegistry.preload_tenant(org.tenant_key)

    tok = create_access_token(
        user_id=created.id,
        org_id=created.org_id,
        tenant_key=org.tenant_key,
        email=created.email,
        role=created.role,
        google_sub=created.google_sub,
    )
    return AuthResponse(access_token=tok, user=_user_public_from_row(created))


# ---------- Sesión ---------------------------------------------------
@protected.get("/me", response_model=MeResponse, tags=["auth"])
def me(uc: UserContext = Depends(deps.require_auth)) -> MeResponse:
    db = get_auth_db()
    u = db.get_user_by_id(uc.user_id)
    if u is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return MeResponse(user=_user_public_from_row(u))


# ---------- Metadata ------------------------------------------------
@protected.get("/variables", response_model=VariablesResponse, tags=["metadata"])
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
@protected.get("/equipos", response_model=EquiposResponse, tags=["equipos"])
def listar_equipos(uc: ListarEquiposUseCase = Depends(deps.get_listar_equipos_uc)):
    return EquiposResponse(equipos=uc.execute())


@protected.get(
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


@protected.get(
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
@protected.get("/flota/resumen", response_model=FlotaResumenResponse, tags=["flota"])
def resumen_flota(uc: ObtenerResumenFlotaUseCase = Depends(deps.get_resumen_flota_uc)):
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
@protected.post(
    "/equipos/{equipo_id}/muestras",
    response_model=PrediccionResponse,
    tags=["muestras"],
)
def registrar_muestra(
    equipo_id: str,
    body: NuevaMuestraRequest,
    uc: RegistrarMuestraUseCase = Depends(deps.get_registrar_muestra_uc),
):
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


@protected.get("/equipos/{equipo_id}/exportar", tags=["equipos"])
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

    rango = ""
    if fecha_desde or fecha_hasta:
        rango = f"_{fecha_desde or 'inicio'}_a_{fecha_hasta or 'hoy'}"
    return _df_to_streaming(df, f"{equipo_id}_historial{rango}", formato)


@protected.get("/flota/exportar", tags=["flota"])
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


# ---------- Admin usuarios ------------------------------------------
@admin_router.get("/users", response_model=AdminUsersResponse)
def admin_list_users(uc: UserContext = Depends(deps.require_admin)):
    db = get_auth_db()
    rows = db.list_users_in_org(uc.org_id)
    return AdminUsersResponse(
        users=[
            AdminUserItem(id=u.id, email=u.email, role=u.role, created_at=u.created_at)
            for u in rows
        ]
    )


@admin_router.patch("/users/{user_id}/role", response_model=AdminUserItem)
def admin_patch_role(
    user_id: int,
    body: AdminRolePatch,
    uc: UserContext = Depends(deps.require_admin),
):
    db = get_auth_db()
    if user_id == uc.user_id and body.role != "ADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="No puedes quitarte tu propio rol de administrador",
        )
    target = db.get_user_by_id(user_id)
    if target is None or target.org_id != uc.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    ok = db.update_user_role(user_id, uc.org_id, body.role)
    if not ok:
        raise HTTPException(status.HTTP_500, detail="No se pudo actualizar")
    updated = db.get_user_by_id(user_id)
    if updated is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Usuario no encontrado tras actualizar")
    return AdminUserItem(
        id=updated.id,
        email=updated.email,
        role=updated.role,
        created_at=updated.created_at,
    )


# Re-export: une todo en `router` para main.py
router.include_router(protected)
router.include_router(auth_router)
router.include_router(admin_router)
