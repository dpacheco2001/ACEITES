"""Contexto de usuario autenticado (request-scoped)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: int = Field(..., ge=1)
    org_id: int = Field(..., ge=1)
    tenant_key: str = Field(..., min_length=1, description="Dominio de correo (empresa)")
    email: str
    role: str  # ADMIN | CLIENTE
    google_sub: str
