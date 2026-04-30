"""Dependencias FastAPI — JWT de sesión y contexto de usuario."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.infrastructure.auth_db import get_auth_db
from src.infrastructure.jwt_session import decode_access_token
from src.interfaces.api.user_context import UserContext

bearer_scheme = HTTPBearer(auto_error=True)


def require_auth(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UserContext:
    token = creds.credentials
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from e

    uid = payload.get("uid")
    if uid is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    db = get_auth_db()
    u = db.get_user_by_id(int(uid))
    if u is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Usuario no existe")

    org = db.get_org_by_id(u.org_id)
    if org is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Organización no existe")

    return UserContext(
        user_id=u.id,
        org_id=u.org_id,
        tenant_key=org.tenant_key,
        email=u.email,
        role=u.role,
        google_sub=u.google_sub,
    )


def require_admin(uc: UserContext = Depends(require_auth)) -> UserContext:
    if uc.role != "ADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return uc
