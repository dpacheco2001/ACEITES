"""Persistencia asyncpg de membresías de organizaciones."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from src.infrastructure.settings import DATABASE_URL


@dataclass
class MembershipRow:
    id: int
    org_id: int
    email: str
    role: str
    status: str
    user_id: Optional[int]
    created_at: str
    accepted_at: Optional[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class MembershipDB:
    def __init__(self, database_url: str = DATABASE_URL) -> None:
        self.database_url = database_url.strip()
        if not self.database_url:
            raise RuntimeError("DATABASE_URL es obligatorio para la persistencia SQL.")
        self._pool: Optional[asyncpg.Pool] = None
        self._init_lock = asyncio.Lock()

    async def init(self) -> None:
        async with self._init_lock:
            if self._pool is not None:
                return
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=30,
            )
            async with self._pool.acquire() as conn:
                await self._init_schema(conn)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def _ready_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            await self.init()
        if self._pool is None:
            raise RuntimeError("Pool SQL no inicializado")
        return self._pool

    async def _init_schema(self, conn) -> None:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS organization_memberships (
                id BIGSERIAL PRIMARY KEY,
                org_id BIGINT NOT NULL REFERENCES organizations(id),
                email TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('ADMIN','CLIENTE')),
                status TEXT NOT NULL CHECK(status IN ('PENDING','ACTIVE')),
                user_id BIGINT REFERENCES users(id),
                created_at TEXT NOT NULL,
                accepted_at TEXT,
                UNIQUE(org_id, email)
            )
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memberships_email ON organization_memberships(email)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memberships_org ON organization_memberships(org_id)"
        )

    async def get_by_email(self, email: str) -> Optional[MembershipRow]:
        row = await self._fetchrow(
            """
            SELECT id, org_id, email, role, status, user_id, created_at, accepted_at
            FROM organization_memberships
            WHERE email = $1
            ORDER BY status = 'ACTIVE' DESC, id DESC
            LIMIT 1
            """,
            email.lower().strip(),
        )
        return self._from_row(row)

    async def list_by_org(self, org_id: int) -> list[MembershipRow]:
        rows = await self._fetch(
            """
            SELECT id, org_id, email, role, status, user_id, created_at, accepted_at
            FROM organization_memberships
            WHERE org_id = $1
            ORDER BY status, email
            """,
            org_id,
        )
        return [m for m in (self._from_row(row) for row in rows) if m]

    async def upsert(
        self,
        org_id: int,
        email: str,
        role: str,
        user_id: Optional[int] = None,
        status: str = "PENDING",
    ) -> MembershipRow:
        now = _utc_now_iso()
        accepted = now if status == "ACTIVE" else None
        row = await self._fetchrow(
            """
            INSERT INTO organization_memberships
                (org_id, email, role, status, user_id, created_at, accepted_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT(org_id, email) DO UPDATE SET
                role = excluded.role,
                status = excluded.status,
                user_id = COALESCE(excluded.user_id, organization_memberships.user_id),
                accepted_at = COALESCE(excluded.accepted_at, organization_memberships.accepted_at)
            RETURNING id, org_id, email, role, status, user_id, created_at, accepted_at
            """,
            org_id,
            email.lower().strip(),
            role,
            status,
            user_id,
            now,
            accepted,
        )
        membership = self._from_row(row)
        if membership is None:
            raise RuntimeError("membership upsert failed")
        return membership

    async def accept(self, membership_id: int, user_id: int) -> bool:
        return await self._execute_bool(
            """
            UPDATE organization_memberships
            SET user_id = $1, status = 'ACTIVE', accepted_at = $2
            WHERE id = $3
            """,
            user_id,
            _utc_now_iso(),
            membership_id,
        )

    async def update_role(self, membership_id: int, org_id: int, role: str) -> bool:
        return await self._execute_bool(
            "UPDATE organization_memberships SET role = $1 WHERE id = $2 AND org_id = $3",
            role,
            membership_id,
            org_id,
        )

    async def _fetchrow(self, sql: str, *args):
        pool = await self._ready_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(sql, *args)

    async def _fetch(self, sql: str, *args):
        pool = await self._ready_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(sql, *args)

    async def _execute_bool(self, sql: str, *args) -> bool:
        pool = await self._ready_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(sql, *args)
        return not result.endswith(" 0")

    @staticmethod
    def _from_row(row) -> Optional[MembershipRow]:
        if row is None:
            return None
        user_id = row["user_id"]
        return MembershipRow(
            id=int(row["id"]),
            org_id=int(row["org_id"]),
            email=row["email"],
            role=row["role"],
            status=row["status"],
            user_id=int(user_id) if user_id is not None else None,
            created_at=row["created_at"],
            accepted_at=row["accepted_at"],
        )


_membership_singleton: Optional[MembershipDB] = None


def get_membership_db() -> MembershipDB:
    global _membership_singleton
    if _membership_singleton is None:
        _membership_singleton = MembershipDB()
    return _membership_singleton
