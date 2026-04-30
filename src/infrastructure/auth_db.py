"""Persistencia SQLite para organizaciones y usuarios autenticados."""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from src.infrastructure.settings import AUTH_DB_PATH


@dataclass
class OrgRow:
    id: int
    tenant_key: str
    created_at: str


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

    def __init__(self, path: Path = AUTH_DB_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS organizations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_key TEXT NOT NULL UNIQUE,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        google_sub TEXT NOT NULL UNIQUE,
                        email TEXT NOT NULL,
                        org_id INTEGER NOT NULL REFERENCES organizations(id),
                        role TEXT NOT NULL CHECK(role IN ('ADMIN','CLIENTE')),
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def get_org_by_id(self, org_id: int) -> Optional[OrgRow]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT id, tenant_key, created_at FROM organizations WHERE id = ?",
                    (org_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return OrgRow(
                    id=row["id"],
                    tenant_key=row["tenant_key"],
                    created_at=row["created_at"],
                )
            finally:
                conn.close()

    def get_org_by_tenant(self, tenant_key: str) -> Optional[OrgRow]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    SELECT id, tenant_key, created_at
                    FROM organizations WHERE tenant_key = ?
                    """,
                    (tenant_key.lower().strip(),),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return OrgRow(
                    id=row["id"],
                    tenant_key=row["tenant_key"],
                    created_at=row["created_at"],
                )
            finally:
                conn.close()

    def create_org(self, tenant_key: str) -> OrgRow:
        tenant = tenant_key.lower().strip()
        now = _utc_now_iso()
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "INSERT INTO organizations (tenant_key, created_at) VALUES (?, ?)",
                    (tenant, now),
                )
                conn.commit()
                return OrgRow(id=int(cur.lastrowid), tenant_key=tenant, created_at=now)
            finally:
                conn.close()

    def count_users_in_org(self, org_id: int) -> int:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "SELECT COUNT(*) AS c FROM users WHERE org_id = ?",
                    (org_id,),
                )
                return int(cur.fetchone()["c"])
            finally:
                conn.close()

    def get_user_by_sub(self, google_sub: str) -> Optional[UserRow]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    SELECT id, google_sub, email, org_id, role, created_at
                    FROM users WHERE google_sub = ?
                    """,
                    (google_sub,),
                )
                row = cur.fetchone()
                return self._user_from_row(row)
            finally:
                conn.close()

    def get_user_by_id(self, user_id: int) -> Optional[UserRow]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    SELECT id, google_sub, email, org_id, role, created_at
                    FROM users WHERE id = ?
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                return self._user_from_row(row)
            finally:
                conn.close()

    def create_user(
        self,
        google_sub: str,
        email: str,
        org_id: int,
        role: str,
    ) -> UserRow:
        now = _utc_now_iso()
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    INSERT INTO users (google_sub, email, org_id, role, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (google_sub, email.lower().strip(), org_id, role, now),
                )
                conn.commit()
                return UserRow(
                    id=int(cur.lastrowid),
                    google_sub=google_sub,
                    email=email.lower().strip(),
                    org_id=org_id,
                    role=role,
                    created_at=now,
                )
            finally:
                conn.close()

    def update_user_role(self, user_id: int, org_id: int, role: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "UPDATE users SET role = ? WHERE id = ? AND org_id = ?",
                    (role, user_id, org_id),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def update_user_membership(self, user_id: int, org_id: int, role: str) -> bool:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "UPDATE users SET org_id = ?, role = ? WHERE id = ?",
                    (org_id, role, user_id),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def list_users_in_org(self, org_id: int) -> List[UserRow]:
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    SELECT id, google_sub, email, org_id, role, created_at
                    FROM users WHERE org_id = ? ORDER BY id
                    """,
                    (org_id,),
                )
                return [
                    row
                    for row in (
                        self._user_from_row(raw)
                        for raw in cur.fetchall()
                    )
                    if row is not None
                ]
            finally:
                conn.close()

    @staticmethod
    def _user_from_row(row: sqlite3.Row | None) -> Optional[UserRow]:
        if row is None:
            return None
        return UserRow(
            id=row["id"],
            google_sub=row["google_sub"],
            email=row["email"],
            org_id=row["org_id"],
            role=row["role"],
            created_at=row["created_at"],
        )


_auth_singleton: Optional[AuthDB] = None


def get_auth_db() -> AuthDB:
    global _auth_singleton
    if _auth_singleton is None:
        _auth_singleton = AuthDB()
    return _auth_singleton
