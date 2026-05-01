"""Dependencias FastAPI para sesión por cookie HttpOnly."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request, status

from src.infrastructure.auth_db import get_auth_db
from src.infrastructure.jwt_session import SessionConfigError, decode_access_token
from src.infrastructure.settings import SESSION_COOKIE_NAME
from src.interfaces.api.user_context import UserContext


def _session_token_from_cookie(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Sesión requerida",
        )
    return token


async def require_auth(request: Request) -> UserContext:
    token = _session_token_from_cookie(request)
    try:
        payload = decode_access_token(token)
    except SessionConfigError as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada",
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida",
        ) from e

    uid = payload.get("uid")
    if uid is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida")

    db = get_auth_db()
    user = await db.get_user_by_id(int(uid))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Usuario no existe")

    org = await db.get_org_by_id(user.org_id)
    if org is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Organización no existe",
        )
    if org.status != "ACTIVE":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Organización desactivada",
        )

    return UserContext(
        user_id=user.id,
        org_id=user.org_id,
        tenant_key=org.tenant_key,
        email=user.email,
        role=user.role,
        google_sub=user.google_sub,
        org_name=org.name,
        is_owner=await db.is_owner_email(user.email),
    )


async def require_admin(uc: UserContext = Depends(require_auth)) -> UserContext:
    if uc.role != "ADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador",
        )
    return uc


async def require_owner(uc: UserContext = Depends(require_auth)) -> UserContext:
    if not uc.is_owner:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Se requiere usuario owner",
        )
    return uc
