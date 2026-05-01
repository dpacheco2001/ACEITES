"""Persistencia Postgres para organizaciones, usuarios y owners."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from psycopg.rows import dict_row
import psycopg

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
    _lock = threading.Lock()

    def __init__(self, database_url: str = DATABASE_URL) -> None:
        self.database_url = database_url.strip()
        if not self.database_url:
            raise RuntimeError("DATABASE_URL es obligatorio para la persistencia SQL.")
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
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
            conn.execute(
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS owner_emails (
                    email TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            self._seed_env_owners(conn)

    def _seed_env_owners(self, conn) -> None:
        now = _utc_now_iso()
        for email in OWNER_EMAILS:
            conn.execute(
                """
                INSERT INTO owner_emails (email, created_at)
                VALUES (%s, %s)
                ON CONFLICT(email) DO NOTHING
                """,
                (email.lower().strip(), now),
            )

    def _fetchone(self, sql: str, params: tuple[Any, ...] = ()):
        with self._lock, self._connect() as conn:
            return conn.execute(sql, params).fetchone()

    def get_org_by_id(self, org_id: int) -> Optional[OrgRow]:
        row = self._fetchone(
            "SELECT id, tenant_key, created_at, name, status FROM organizations WHERE id = %s",
            (org_id,),
        )
        return self._org_from_row(row)

    def get_org_by_tenant(self, tenant_key: str) -> Optional[OrgRow]:
        row = self._fetchone(
            "SELECT id, tenant_key, created_at, name, status FROM organizations WHERE tenant_key = %s",
            (tenant_key.lower().strip(),),
        )
        return self._org_from_row(row)

    def create_org(self, tenant_key: str, name: str = "") -> OrgRow:
        tenant = tenant_key.lower().strip()
        row = self._write_returning(
            """
            INSERT INTO organizations (tenant_key, created_at, name, status)
            VALUES (%s, %s, %s, 'ACTIVE')
            RETURNING id, tenant_key, created_at, name, status
            """,
            (tenant, _utc_now_iso(), name.strip() or tenant),
        )
        org = self._org_from_row(row)
        if org is None:
            raise RuntimeError("organization create failed")
        return org

    def upsert_org(self, tenant_key: str, name: str) -> OrgRow:
        existing = self.get_org_by_tenant(tenant_key)
        if existing is None:
            return self.create_org(tenant_key, name)
        if existing.status != "ACTIVE":
            self.update_org_status(existing.id, "ACTIVE")
            refreshed = self.get_org_by_id(existing.id)
            if refreshed is not None:
                return refreshed
        return existing

    def list_orgs(self, include_deleted: bool = True) -> list[OrgRow]:
        where = "" if include_deleted else "WHERE status = 'ACTIVE'"
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                f"SELECT id, tenant_key, created_at, name, status FROM organizations {where} ORDER BY id"
            ).fetchall()
        return [org for org in (self._org_from_row(row) for row in rows) if org]

    def update_org_status(self, org_id: int, status: str) -> bool:
        return self._execute_bool(
            "UPDATE organizations SET status = %s WHERE id = %s",
            (status, org_id),
        )

    def count_users_in_org(self, org_id: int) -> int:
        row = self._fetchone("SELECT COUNT(*) AS c FROM users WHERE org_id = %s", (org_id,))
        return int(row["c"] if row is not None else 0)

    def get_user_by_sub(self, google_sub: str) -> Optional[UserRow]:
        row = self._fetchone(
            "SELECT id, google_sub, email, org_id, role, created_at FROM users WHERE google_sub = %s",
            (google_sub,),
        )
        return self._user_from_row(row)

    def get_user_by_id(self, user_id: int) -> Optional[UserRow]:
        row = self._fetchone(
            "SELECT id, google_sub, email, org_id, role, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return self._user_from_row(row)

    def create_user(self, google_sub: str, email: str, org_id: int, role: str) -> UserRow:
        row = self._write_returning(
            """
            INSERT INTO users (google_sub, email, org_id, role, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, google_sub, email, org_id, role, created_at
            """,
            (google_sub, email.lower().strip(), org_id, role, _utc_now_iso()),
        )
        user = self._user_from_row(row)
        if user is None:
            raise RuntimeError("user create failed")
        return user

    def update_user_role(self, user_id: int, org_id: int, role: str) -> bool:
        return self._execute_bool(
            "UPDATE users SET role = %s WHERE id = %s AND org_id = %s",
            (role, user_id, org_id),
        )

    def update_user_membership(self, user_id: int, org_id: int, role: str) -> bool:
        return self._execute_bool(
            "UPDATE users SET org_id = %s, role = %s WHERE id = %s",
            (org_id, role, user_id),
        )

    def list_users_in_org(self, org_id: int) -> list[UserRow]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, google_sub, email, org_id, role, created_at
                FROM users WHERE org_id = %s ORDER BY id
                """,
                (org_id,),
            ).fetchall()
        return [user for user in (self._user_from_row(row) for row in rows) if user]

    def add_owner_email(self, email: str) -> None:
        self._execute_bool(
            """
            INSERT INTO owner_emails (email, created_at)
            VALUES (%s, %s)
            ON CONFLICT(email) DO NOTHING
            """,
            (email.lower().strip(), _utc_now_iso()),
        )

    def is_owner_email(self, email: str) -> bool:
        clean = email.lower().strip()
        row = self._fetchone("SELECT email FROM owner_emails WHERE email = %s", (clean,))
        return row is not None or clean in OWNER_EMAILS

    def _write_returning(self, sql: str, params: tuple[Any, ...]):
        with self._lock, self._connect() as conn:
            return conn.execute(sql, params).fetchone()

    def _execute_bool(self, sql: str, params: tuple[Any, ...]) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(sql, params)
            return cur.rowcount > 0

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
