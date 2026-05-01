"""Rutas de autenticación y sesión."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.infrastructure.auth_db import UserRow, get_auth_db
from src.infrastructure.google_id_token import verify_google_id_token
from src.infrastructure.jwt_session import SessionConfigError, create_access_token
from src.infrastructure.membership_db import get_membership_db
from src.infrastructure.settings import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    GOOGLE_CLIENT_ID,
    JWT_SECRET,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
)
from src.infrastructure.tenant_excel_registry import TenantExcelRegistry
from src.interfaces.api import dependencies as deps
from src.interfaces.api.schemas import (
    AuthResponse,
    GoogleAuthRequest,
    GoogleClientConfigResponse,
    LogoutResponse,
    MeResponse,
    UserPublic,
)
from src.interfaces.api.user_context import UserContext

router = APIRouter(tags=["auth"])


def _tenant_for_user(google_sub: str) -> str:
    digest = hashlib.sha256(google_sub.encode("utf-8")).hexdigest()[:16]
    return f"user-{digest}"


async def _user_public_from_row(user: UserRow) -> UserPublic:
    db = get_auth_db()
    org = await db.get_org_by_id(user.org_id)
    tenant_key = org.tenant_key if org else ""
    return UserPublic(
        id=user.id,
        email=user.email,
        org_id=user.org_id,
        tenant_key=tenant_key,
        role=user.role,
        org_name=org.name if org else "",
        dataset_loaded=TenantExcelRegistry.has_tenant_dataset(tenant_key)
        if tenant_key
        else False,
        is_owner=await db.is_owner_email(user.email),
    )


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )


async def _build_session_response(response: Response, user: UserRow) -> AuthResponse:
    db = get_auth_db()
    org = await db.get_org_by_id(user.org_id)
    if org is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inconsistencia de organización",
        )
    try:
        token = create_access_token(
            user_id=user.id,
            org_id=user.org_id,
            tenant_key=org.tenant_key,
            email=user.email,
            role=user.role,
            google_sub=user.google_sub,
        )
    except SessionConfigError as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    _set_session_cookie(response, token)
    return AuthResponse(
        user=await _user_public_from_row(user),
        expires_in_seconds=ACCESS_TOKEN_EXPIRE_SECONDS,
    )


@router.get("/auth/client-config", response_model=GoogleClientConfigResponse)
def auth_client_config() -> GoogleClientConfigResponse:
    return GoogleClientConfigResponse(google_client_id=GOOGLE_CLIENT_ID or "")


@router.post("/auth/google", response_model=AuthResponse)
async def auth_google(body: GoogleAuthRequest, response: Response) -> AuthResponse:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GOOGLE_CLIENT_ID no configurado en el servidor",
        )
    if not JWT_SECRET:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET no configurado en el servidor",
        )

    try:
        info = verify_google_id_token(body.id_token)
    except Exception as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=f"Token de Google inválido: {e}",
        ) from e

    email_raw = info.get("email") or ""
    if not isinstance(email_raw, str) or "@" not in email_raw:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Google no devolvió email válido",
        )
    if not info.get("email_verified"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="El correo de Google debe estar verificado",
        )

    email = email_raw.lower().strip()
    google_sub = str(info["sub"])
    tenant_key = _tenant_for_user(google_sub)

    db = get_auth_db()
    memberships = get_membership_db()
    invited = await memberships.get_by_email(email)
    existing = await db.get_user_by_sub(google_sub)

    if invited is not None:
        org = await db.get_org_by_id(invited.org_id)
        if org is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La membresía apunta a una organización inexistente",
            )
        if existing is None:
            existing = await db.create_user(
                google_sub=google_sub,
                email=email,
                org_id=org.id,
                role=invited.role,
            )
        elif existing.org_id != org.id or existing.role != invited.role:
            await db.update_user_membership(existing.id, org.id, invited.role)
            updated = await db.get_user_by_id(existing.id)
            if updated is None:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No se pudo actualizar la organización del usuario",
                )
            existing = updated
        await memberships.accept(invited.id, existing.id)
        if TenantExcelRegistry.has_tenant_dataset(org.tenant_key):
            TenantExcelRegistry.preload_tenant(org.tenant_key)
        return await _build_session_response(response, existing)

    if existing is not None:
        org = await db.get_org_by_id(existing.org_id)
        if org is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Inconsistencia de organización",
            )
        if TenantExcelRegistry.has_tenant_dataset(org.tenant_key):
            TenantExcelRegistry.preload_tenant(org.tenant_key)
        return await _build_session_response(response, existing)

    org = await db.get_org_by_tenant(tenant_key)
    if org is None:
        org = await db.create_org(tenant_key)

    role = "ADMIN" if await db.count_users_in_org(org.id) == 0 else "CLIENTE"
    created = await db.create_user(
        google_sub=google_sub,
        email=email,
        org_id=org.id,
        role=role,
    )
    if TenantExcelRegistry.has_tenant_dataset(org.tenant_key):
        TenantExcelRegistry.preload_tenant(org.tenant_key)
    return await _build_session_response(response, created)


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(response: Response) -> LogoutResponse:
    _clear_session_cookie(response)
    return LogoutResponse(ok=True)


@router.get("/me", response_model=MeResponse)
async def me(uc: UserContext = Depends(deps.require_auth)) -> MeResponse:
    user = await get_auth_db().get_user_by_id(uc.user_id)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    return MeResponse(user=await _user_public_from_row(user))
