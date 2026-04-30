"""JWT de sesión propia (HS256) tras login Google."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from src.infrastructure.settings import JWT_ALGORITHM, JWT_EXPIRE_HOURS, JWT_SECRET


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
    exp = now + timedelta(hours=JWT_EXPIRE_HOURS)
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
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
