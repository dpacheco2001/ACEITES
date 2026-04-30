"""Schemas Pydantic — contrato de entrada/salida de la API."""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.infrastructure.settings import VARIABLES_ANALITICAS


# ======================================================================
# Responses
# ======================================================================
class HealthResponse(BaseModel):
    status: str
    modelos_cargados: bool


class EquiposResponse(BaseModel):
    equipos: List[str]


class ResumenEquipoSchema(BaseModel):
    equipo: str
    semaforo: str
    estado_modelo: str
    horas_actuales: float
    horas_hasta_critico: Optional[float]
    ultima_muestra_fecha: Optional[date]
    total_muestras: int
    historia_suficiente: bool = True
    horas_htc_confiable: bool = True


class FlotaResumenResponse(BaseModel):
    total_equipos: int
    criticos: int
    precaucion: int
    normales: int
    equipos: List[ResumenEquipoSchema]


class PrediccionResponse(BaseModel):
    equipo: str
    semaforo: str
    estado_modelo: str
    horas_actuales: float
    horas_hasta_critico: Optional[float]
    predicciones_t1: Dict[str, float]
    variables_baja_confianza: List[str]
    ultima_muestra_fecha: Optional[date]
    historia_suficiente: bool = True
    horas_htc_confiable: bool = True
    advertencias: List[str] = []


class MuestraHistorial(BaseModel):
    fecha: Optional[date]
    hora_producto: float
    estado: Optional[str]
    valores: Dict[str, float]


class HistorialResponse(BaseModel):
    equipo: str
    total_muestras: int
    historial: List[MuestraHistorial]


# ======================================================================
# Requests
# ======================================================================
class NuevaMuestraRequest(BaseModel):
    fecha: date
    hora_producto: float = Field(gt=0)
    estado: Optional[str] = None
    # Los 12 valores — requeridos, positivos
    valores: Dict[str, float]

    @classmethod
    def variables_esperadas(cls) -> List[str]:
        return list(VARIABLES_ANALITICAS)


# ======================================================================
# Metadatos
# ======================================================================
class LimiteAlertaSchema(BaseModel):
    variable: str
    direccion: str
    verde_min: Optional[float] = None
    verde_max: Optional[float] = None
    amarillo_min: Optional[float] = None
    amarillo_max: Optional[float] = None
    rojo_min: Optional[float] = None
    rojo_max: Optional[float] = None


class VariablesResponse(BaseModel):
    variables: List[str]
    baja_confianza: List[str]
    limites: List[LimiteAlertaSchema]


# ======================================================================
# Autenticación / admin
# ======================================================================
class GoogleClientConfigResponse(BaseModel):
    google_client_id: str = ""


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=10)


class UserPublic(BaseModel):
    id: int
    email: str
    org_id: int
    tenant_key: str
    role: str


class AuthResponse(BaseModel):
    user: UserPublic
    expires_in_seconds: int


class MeResponse(BaseModel):
    user: UserPublic


class LogoutResponse(BaseModel):
    ok: bool = True


class AdminUserItem(BaseModel):
    id: int
    email: str
    role: str
    created_at: str


class AdminUsersResponse(BaseModel):
    users: List[AdminUserItem]


class AdminRolePatch(BaseModel):
    role: str = Field(pattern="^(ADMIN|CLIENTE)$")


# ======================================================================
# Atlas
# ======================================================================
class AtlasSliceRequest(BaseModel):
    equipo_id: Optional[str] = None
    variables: Optional[List[str]] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    max_rows: int = Field(default=500, ge=1, le=1000)
