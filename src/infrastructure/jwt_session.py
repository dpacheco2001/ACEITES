"""JWT de sesión propia tras login Google."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from src.infrastructure.settings import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET,
)


class SessionConfigError(RuntimeError):
    """Configuración de sesión faltante o insegura."""


def _jwt_secret() -> str:
    if not JWT_SECRET:
        raise SessionConfigError("JWT_SECRET no está configurado")
    if len(JWT_SECRET.encode("utf-8")) < 32:
        raise SessionConfigError("JWT_SECRET debe tener al menos 32 bytes")
    return JWT_SECRET


def create_access_token(
    *,
    user_id: int,
    org_id: int,
    tenant_key: str,
    email: str,
    role: str,
    google_sub: str,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {
        "sub": google_sub,
        "uid": user_id,
        "oid": org_id,
        "tenant": tenant_key,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
