"""Persistencia Postgres de membresías de organizaciones."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from psycopg.rows import dict_row
import psycopg

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
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memberships_email ON organization_memberships(email)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memberships_org ON organization_memberships(org_id)"
            )

    def get_by_email(self, email: str) -> Optional[MembershipRow]:
        row = self._fetchone(
            """
            SELECT id, org_id, email, role, status, user_id, created_at, accepted_at
            FROM organization_memberships
            WHERE email = %s
            ORDER BY status = 'ACTIVE' DESC, id DESC
            LIMIT 1
            """,
            (email.lower().strip(),),
        )
        return self._from_row(row)

    def list_by_org(self, org_id: int) -> list[MembershipRow]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, org_id, email, role, status, user_id, created_at, accepted_at
                FROM organization_memberships
                WHERE org_id = %s
                ORDER BY status, email
                """,
                (org_id,),
            ).fetchall()
        return [m for m in (self._from_row(row) for row in rows) if m]

    def upsert(
        self,
        org_id: int,
        email: str,
        role: str,
        user_id: Optional[int] = None,
        status: str = "PENDING",
    ) -> MembershipRow:
        now = _utc_now_iso()
        accepted = now if status == "ACTIVE" else None
        row = self._write_returning(
            """
            INSERT INTO organization_memberships
                (org_id, email, role, status, user_id, created_at, accepted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(org_id, email) DO UPDATE SET
                role = excluded.role,
                status = excluded.status,
                user_id = COALESCE(excluded.user_id, organization_memberships.user_id),
                accepted_at = COALESCE(excluded.accepted_at, organization_memberships.accepted_at)
            RETURNING id, org_id, email, role, status, user_id, created_at, accepted_at
            """,
            (org_id, email.lower().strip(), role, status, user_id, now, accepted),
        )
        membership = self._from_row(row)
        if membership is None:
            raise RuntimeError("membership upsert failed")
        return membership

    def accept(self, membership_id: int, user_id: int) -> bool:
        return self._execute_bool(
            """
            UPDATE organization_memberships
            SET user_id = %s, status = 'ACTIVE', accepted_at = %s
            WHERE id = %s
            """,
            (user_id, _utc_now_iso(), membership_id),
        )

    def update_role(self, membership_id: int, org_id: int, role: str) -> bool:
        return self._execute_bool(
            "UPDATE organization_memberships SET role = %s WHERE id = %s AND org_id = %s",
            (role, membership_id, org_id),
        )

    def _fetchone(self, sql: str, params: tuple[Any, ...]):
        with self._lock, self._connect() as conn:
            return conn.execute(sql, params).fetchone()

    def _write_returning(self, sql: str, params: tuple[Any, ...]):
        with self._lock, self._connect() as conn:
            return conn.execute(sql, params).fetchone()

    def _execute_bool(self, sql: str, params: tuple[Any, ...]) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(sql, params)
            return cur.rowcount > 0

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
