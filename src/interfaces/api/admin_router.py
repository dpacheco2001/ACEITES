"""Rutas administrativas."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.infrastructure.auth_db import get_auth_db
from src.interfaces.api import dependencies as deps
from src.interfaces.api.schemas import AdminRolePatch, AdminUserItem, AdminUsersResponse
from src.interfaces.api.user_context import UserContext

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUsersResponse)
def admin_list_users(uc: UserContext = Depends(deps.require_admin)) -> AdminUsersResponse:
    rows = get_auth_db().list_users_in_org(uc.org_id)
    return AdminUsersResponse(
        users=[
            AdminUserItem(
                id=user.id,
                email=user.email,
                role=user.role,
                created_at=user.created_at,
            )
            for user in rows
        ]
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserItem)
def admin_patch_role(
    user_id: int,
    body: AdminRolePatch,
    uc: UserContext = Depends(deps.require_admin),
) -> AdminUserItem:
    db = get_auth_db()
    if user_id == uc.user_id and body.role != "ADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="No puedes quitarte tu propio rol de administrador",
        )

    target = db.get_user_by_id(user_id)
    if target is None or target.org_id != uc.org_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if not db.update_user_role(user_id, uc.org_id, body.role):
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar",
        )

    updated = db.get_user_by_id(user_id)
    if updated is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Usuario no encontrado tras actualizar",
        )
    return AdminUserItem(
        id=updated.id,
        email=updated.email,
        role=updated.role,
        created_at=updated.created_at,
    )
