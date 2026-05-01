"""Contexto de usuario autenticado para cada request."""
from __future__ import annotations

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: int = Field(..., ge=1)
    org_id: int = Field(..., ge=1)
    tenant_key: str = Field(..., min_length=1)
    email: str
    role: str
    google_sub: str
    org_name: str = ""
    is_owner: bool = False
