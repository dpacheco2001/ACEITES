"""Schemas Pydantic — contrato de entrada/salida de la API."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

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
    org_name: str = ""
    dataset_loaded: bool = False
    is_owner: bool = False


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


class AdminRolePatch(BaseModel):
    role: str = Field(pattern="^(ADMIN|CLIENTE)$")


class AdminMembershipItem(BaseModel):
    id: int
    email: str
    role: str
    status: str
    user_id: Optional[int] = None
    created_at: str


class AdminUsersResponse(BaseModel):
    users: List[AdminUserItem]
    memberships: List[AdminMembershipItem] = []


class AdminMembershipCreate(BaseModel):
    email: str = Field(..., min_length=3)
    role: str = Field(default="CLIENTE", pattern="^(ADMIN|CLIENTE)$")


class OwnerOrgItem(BaseModel):
    id: int
    tenant_key: str
    name: str
    status: str
    created_at: str
    user_count: int = 0
    dataset_loaded: bool = False
    dataset_rows: int = 0
    dataset_equipos: int = 0
    admin_emails: List[str] = []


class OwnerOrgsResponse(BaseModel):
    organizations: List[OwnerOrgItem]


class OwnerOrgCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    admin_email: str = Field(..., min_length=3)


class OwnerTransferRequest(BaseModel):
    email: str = Field(..., min_length=3)


class DatasetStatusResponse(BaseModel):
    loaded: bool
    tenant_key: str
    org_name: str = ""
    total_rows: int = 0
    total_equipos: int = 0
    required_headers: List[str]
    optional_headers: List[str]
    errors: List[str] = []
    warnings: List[str] = []


class DatasetValidationResponse(BaseModel):
    ok: bool
    total_rows: int
    total_equipos: int
    missing_headers: List[str]
    errors: List[str]
    warnings: List[str]
    headers: List[str]
    required_headers: List[str]
    optional_headers: List[str]


class DatasetPreviewResponse(BaseModel):
    loaded: bool
    tenant_key: str
    org_name: str = ""
    total_rows: int = 0
    total_equipos: int = 0
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []


# ======================================================================
# Atlas
# ======================================================================
class AtlasSliceRequest(BaseModel):
    equipo_id: Optional[str] = None
    variables: Optional[List[str]] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    max_rows: int = Field(default=500, ge=1, le=1000)
