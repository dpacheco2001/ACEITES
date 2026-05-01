"""Persistencia asyncpg para organizaciones, usuarios y owners."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from src.infrastructure.settings import DATABASE_URL, OWNER_EMAILS


@dataclass
class OrgRow:
    id: int
    tenant_key: str
    created_at: str
    name: str = ""
    status: str = "ACTIVE"


@dataclass
class UserRow:
    id: int
    google_sub: str
    email: str
    org_id: int
    role: str
    created_at: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class AuthDB:
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
            CREATE TABLE IF NOT EXISTS organizations (
                id BIGSERIAL PRIMARY KEY,
                tenant_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ACTIVE'
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                google_sub TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                org_id BIGINT NOT NULL REFERENCES organizations(id),
                role TEXT NOT NULL CHECK(role IN ('ADMIN','CLIENTE')),
                created_at TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS owner_emails (
                email TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        await self._seed_env_owners(conn)

    async def _seed_env_owners(self, conn) -> None:
        now = _utc_now_iso()
        for email in OWNER_EMAILS:
            await conn.execute(
                """
                INSERT INTO owner_emails (email, created_at)
                VALUES ($1, $2)
                ON CONFLICT(email) DO NOTHING
                """,
                email.lower().strip(),
                now,
            )

    async def get_org_by_id(self, org_id: int) -> Optional[OrgRow]:
        row = await self._fetchrow(
            "SELECT id, tenant_key, created_at, name, status FROM organizations WHERE id = $1",
            org_id,
        )
        return self._org_from_row(row)

    async def get_org_by_tenant(self, tenant_key: str) -> Optional[OrgRow]:
        row = await self._fetchrow(
            "SELECT id, tenant_key, created_at, name, status FROM organizations WHERE tenant_key = $1",
            tenant_key.lower().strip(),
        )
        return self._org_from_row(row)

    async def create_org(self, tenant_key: str, name: str = "") -> OrgRow:
        tenant = tenant_key.lower().strip()
        row = await self._fetchrow(
            """
            INSERT INTO organizations (tenant_key, created_at, name, status)
            VALUES ($1, $2, $3, 'ACTIVE')
            RETURNING id, tenant_key, created_at, name, status
            """,
            tenant,
            _utc_now_iso(),
            name.strip() or tenant,
        )
        org = self._org_from_row(row)
        if org is None:
            raise RuntimeError("organization create failed")
        return org

    async def upsert_org(self, tenant_key: str, name: str) -> OrgRow:
        existing = await self.get_org_by_tenant(tenant_key)
        if existing is None:
            return await self.create_org(tenant_key, name)
        if existing.status != "ACTIVE":
            await self.update_org_status(existing.id, "ACTIVE")
            refreshed = await self.get_org_by_id(existing.id)
            if refreshed is not None:
                return refreshed
        return existing

    async def list_orgs(self, include_deleted: bool = True) -> list[OrgRow]:
        where = "" if include_deleted else "WHERE status = 'ACTIVE'"
        rows = await self._fetch(
            f"SELECT id, tenant_key, created_at, name, status FROM organizations {where} ORDER BY id"
        )
        return [org for org in (self._org_from_row(row) for row in rows) if org]

    async def update_org_status(self, org_id: int, status: str) -> bool:
        return await self._execute_bool(
            "UPDATE organizations SET status = $1 WHERE id = $2",
            status,
            org_id,
        )

    async def count_users_in_org(self, org_id: int) -> int:
        row = await self._fetchrow("SELECT COUNT(*) AS c FROM users WHERE org_id = $1", org_id)
        return int(row["c"] if row is not None else 0)

    async def get_user_by_sub(self, google_sub: str) -> Optional[UserRow]:
        row = await self._fetchrow(
            "SELECT id, google_sub, email, org_id, role, created_at FROM users WHERE google_sub = $1",
            google_sub,
        )
        return self._user_from_row(row)

    async def get_user_by_id(self, user_id: int) -> Optional[UserRow]:
        row = await self._fetchrow(
            "SELECT id, google_sub, email, org_id, role, created_at FROM users WHERE id = $1",
            user_id,
        )
        return self._user_from_row(row)

    async def create_user(self, google_sub: str, email: str, org_id: int, role: str) -> UserRow:
        row = await self._fetchrow(
            """
            INSERT INTO users (google_sub, email, org_id, role, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, google_sub, email, org_id, role, created_at
            """,
            google_sub,
            email.lower().strip(),
            org_id,
            role,
            _utc_now_iso(),
        )
        user = self._user_from_row(row)
        if user is None:
            raise RuntimeError("user create failed")
        return user

    async def update_user_role(self, user_id: int, org_id: int, role: str) -> bool:
        return await self._execute_bool(
            "UPDATE users SET role = $1 WHERE id = $2 AND org_id = $3",
            role,
            user_id,
            org_id,
        )

    async def update_user_membership(self, user_id: int, org_id: int, role: str) -> bool:
        return await self._execute_bool(
            "UPDATE users SET org_id = $1, role = $2 WHERE id = $3",
            org_id,
            role,
            user_id,
        )

    async def list_users_in_org(self, org_id: int) -> list[UserRow]:
        rows = await self._fetch(
            """
            SELECT id, google_sub, email, org_id, role, created_at
            FROM users WHERE org_id = $1 ORDER BY id
            """,
            org_id,
        )
        return [user for user in (self._user_from_row(row) for row in rows) if user]

    async def add_owner_email(self, email: str) -> None:
        await self._execute_bool(
            """
            INSERT INTO owner_emails (email, created_at)
            VALUES ($1, $2)
            ON CONFLICT(email) DO NOTHING
            """,
            email.lower().strip(),
            _utc_now_iso(),
        )

    async def is_owner_email(self, email: str) -> bool:
        clean = email.lower().strip()
        row = await self._fetchrow("SELECT email FROM owner_emails WHERE email = $1", clean)
        return row is not None or clean in OWNER_EMAILS

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
    def _org_from_row(row) -> Optional[OrgRow]:
        if row is None:
            return None
        return OrgRow(
            id=int(row["id"]),
            tenant_key=row["tenant_key"],
            created_at=row["created_at"],
            name=row["name"],
            status=row["status"],
        )

    @staticmethod
    def _user_from_row(row) -> Optional[UserRow]:
        if row is None:
            return None
        return UserRow(
            id=int(row["id"]),
            google_sub=row["google_sub"],
            email=row["email"],
            org_id=int(row["org_id"]),
            role=row["role"],
            created_at=row["created_at"],
        )


_auth_singleton: Optional[AuthDB] = None


def get_auth_db() -> AuthDB:
    global _auth_singleton
    if _auth_singleton is None:
        _auth_singleton = AuthDB()
    return _auth_singleton
