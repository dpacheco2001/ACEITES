"""Rutas owner para administrar organizaciones OilMine."""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, status

from src.infrastructure.auth_db import get_auth_db
from src.infrastructure.membership_db import get_membership_db
from src.infrastructure.tenant_excel_registry import TenantExcelRegistry
from src.interfaces.api import dependencies as deps
from src.interfaces.api.schemas import (
    OwnerOrgCreate,
    OwnerOrgItem,
    OwnerTransferRequest,
    OwnerOrgsResponse,
)
from src.interfaces.api.user_context import UserContext

router = APIRouter(prefix="/owner", tags=["owner"])

_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")


def _slugify_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.strip().lower())
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    return slug[:48] or "org"


def _next_tenant_key(name: str) -> str:
    db = get_auth_db()
    base = _slugify_name(name)
    candidate = base
    suffix = 2
    while db.get_org_by_tenant(candidate) is not None:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _dataset_counts(tenant_key: str) -> tuple[bool, int, int]:
    if not TenantExcelRegistry.has_tenant_dataset(tenant_key):
        return False, 0, 0
    try:
        df = TenantExcelRegistry.get_manager(tenant_key).dataframe()
    except Exception:
        return True, 0, 0
    equipos = int(df["Equipo"].nunique()) if "Equipo" in df.columns else 0
    return True, int(len(df)), equipos


def _org_item(org) -> OwnerOrgItem:
    auth_db = get_auth_db()
    memberships = get_membership_db().list_by_org(org.id)
    loaded, rows, equipos = _dataset_counts(org.tenant_key)
    admin_emails = [
        item.email
        for item in memberships
        if item.role == "ADMIN" and item.status in {"ACTIVE", "PENDING"}
    ]
    return OwnerOrgItem(
        id=org.id,
        tenant_key=org.tenant_key,
        name=org.name,
        status=org.status,
        created_at=org.created_at,
        user_count=auth_db.count_users_in_org(org.id),
        dataset_loaded=loaded,
        dataset_rows=rows,
        dataset_equipos=equipos,
        admin_emails=admin_emails,
    )


@router.get("/organizations", response_model=OwnerOrgsResponse)
def list_organizations(
    uc: UserContext = Depends(deps.require_owner),
) -> OwnerOrgsResponse:
    del uc
    return OwnerOrgsResponse(
        organizations=[_org_item(org) for org in get_auth_db().list_orgs()]
    )


@router.post("/organizations", response_model=OwnerOrgItem)
def create_organization(
    body: OwnerOrgCreate,
    uc: UserContext = Depends(deps.require_owner),
) -> OwnerOrgItem:
    del uc
    tenant_key = _next_tenant_key(body.name)
    admin_email = body.admin_email.lower().strip()
    if not _TENANT_RE.match(tenant_key):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tenant_key debe usar letras, numeros, guion o guion bajo",
        )
    if "@" not in admin_email:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email inválido")

    auth_db = get_auth_db()
    org = auth_db.upsert_org(tenant_key, body.name.strip())
    user = next((u for u in auth_db.list_users_in_org(org.id) if u.email == admin_email), None)
    if user is not None and user.role != "ADMIN":
        auth_db.update_user_role(user.id, org.id, "ADMIN")

    get_membership_db().upsert(
        org_id=org.id,
        email=admin_email,
        role="ADMIN",
        user_id=user.id if user else None,
        status="ACTIVE" if user else "PENDING",
    )
    return _org_item(org)


@router.post("/owners/transfer", response_model=OwnerOrgsResponse)
def transfer_owner(
    body: OwnerTransferRequest,
    uc: UserContext = Depends(deps.require_owner),
) -> OwnerOrgsResponse:
    email = body.email.lower().strip()
    if "@" not in email:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email inválido")
    get_auth_db().add_owner_email(email)
    return list_organizations(uc)


@router.delete("/organizations/{org_id}", response_model=OwnerOrgItem)
def delete_organization(
    org_id: int,
    uc: UserContext = Depends(deps.require_owner),
) -> OwnerOrgItem:
    if org_id == uc.org_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="No puedes desactivar la organización de tu sesión actual",
        )
    db = get_auth_db()
    org = db.get_org_by_id(org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")
    db.update_org_status(org_id, "DELETED")
    updated = db.get_org_by_id(org_id)
    return _org_item(updated)
