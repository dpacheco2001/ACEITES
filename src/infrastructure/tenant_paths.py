"""Rutas de datos por tenant (empresa) — paths seguros en disco."""
from __future__ import annotations

import re
from pathlib import Path

from src.infrastructure.settings import EXCEL_FILENAME, ROOT_DIR, TENANTS_ROOT


def sanitize_tenant_key(tenant_key: str) -> str:
    """Normaliza el dominio de correo a un segmento de carpeta seguro."""
    s = tenant_key.strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = s.strip("._-") or "tenant"
    return s[:200]


def tenant_data_dir(tenant_key: str) -> Path:
    return TENANTS_ROOT / sanitize_tenant_key(tenant_key)


def tenant_excel_path(tenant_key: str) -> Path:
    return tenant_data_dir(tenant_key) / EXCEL_FILENAME
