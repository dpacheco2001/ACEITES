"""Rutas administrativas."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.infrastructure.auth_db import get_auth_db
from src.infrastructure.membership_db import get_membership_db
from src.interfaces.api import dependencies as deps
from src.interfaces.api.schemas import (
    AdminMembershipCreate,
    AdminMembershipItem,
    AdminRolePatch,
    AdminUserItem,
    AdminUsersResponse,
)
from src.interfaces.api.user_context import UserContext

router = APIRouter(prefix="/admin", tags=["admin"])


def _visible_users(rows, uc: UserContext):
    by_email = {}
    for user in rows:
        existing = by_email.get(user.email)
        if existing is None or user.id == uc.user_id:
            by_email[user.email] = user
    return sorted(by_email.values(), key=lambda user: user.email)


@router.get("/users", response_model=AdminUsersResponse)
async def admin_list_users(uc: UserContext = Depends(deps.require_admin)) -> AdminUsersResponse:
    memberships = await get_membership_db().list_by_org(uc.org_id)
    rows = _visible_users(await get_auth_db().list_users_in_org(uc.org_id), uc)
    return AdminUsersResponse(
        users=[
            AdminUserItem(
                id=user.id,
                email=user.email,
                role=user.role,
                created_at=user.created_at,
            )
            for user in rows
        ],
        memberships=[
            AdminMembershipItem(
                id=item.id,
                email=item.email,
                role=item.role,
                status=item.status,
                user_id=item.user_id,
                created_at=item.created_at,
            )
            for item in memberships
        ],
    )


@router.post("/members", response_model=AdminMembershipItem)
async def admin_add_member(
    body: AdminMembershipCreate,
    uc: UserContext = Depends(deps.require_admin),
) -> AdminMembershipItem:
    email = body.email.lower().strip()
    if "@" not in email:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email inválido")

    db = get_auth_db()
    user = next((u for u in await db.list_users_in_org(uc.org_id) if u.email == email), None)
    if user is not None and user.id == uc.user_id and body.role != "ADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="No puedes quitarte tu propio rol de administrador",
        )
    membership = await get_membership_db().upsert(
        org_id=uc.org_id,
        email=email,
        role=body.role,
        user_id=user.id if user else None,
        status="ACTIVE" if user else "PENDING",
    )
    if user and user.email == uc.email and body.role != "ADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="No puedes quitarte tu propio rol de administrador",
        )
    if user and user.role != body.role:
        await db.update_user_role(user.id, uc.org_id, body.role)
    return AdminMembershipItem(
        id=membership.id,
        email=membership.email,
        role=membership.role,
        status=membership.status,
        user_id=membership.user_id,
        created_at=membership.created_at,
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserItem)
async def admin_patch_role(
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

    target = await db.get_user_by_id(user_id)
    if target is None or target.org_id != uc.org_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    if target.email == uc.email and body.role != "ADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="No puedes quitarte tu propio rol de administrador",
        )

    if not await db.update_user_role(user_id, uc.org_id, body.role):
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar",
        )
    await get_membership_db().upsert(
        org_id=uc.org_id,
        email=target.email,
        role=body.role,
        user_id=target.id,
        status="ACTIVE",
    )

    updated = await db.get_user_by_id(user_id)
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


@router.patch("/members/{membership_id}/role", response_model=AdminMembershipItem)
async def admin_patch_member_role(
    membership_id: int,
    body: AdminRolePatch,
    uc: UserContext = Depends(deps.require_admin),
) -> AdminMembershipItem:
    memberships = get_membership_db()
    target = next(
        (item for item in await memberships.list_by_org(uc.org_id) if item.id == membership_id),
        None,
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Membresía no encontrada")
    if (target.user_id == uc.user_id or target.email == uc.email) and body.role != "ADMIN":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="No puedes quitarte tu propio rol de administrador",
        )
    if not await memberships.update_role(membership_id, uc.org_id, body.role):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo actualizar")
    if target.user_id:
        await get_auth_db().update_user_role(target.user_id, uc.org_id, body.role)
    updated = next(
        item for item in await memberships.list_by_org(uc.org_id) if item.id == membership_id
    )
    return AdminMembershipItem(
        id=updated.id,
        email=updated.email,
        role=updated.role,
        status=updated.status,
        user_id=updated.user_id,
        created_at=updated.created_at,
    )
