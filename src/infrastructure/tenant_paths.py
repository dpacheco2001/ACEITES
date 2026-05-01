"""Rutas de datos por tenant."""
from __future__ import annotations

import re
from pathlib import Path

from src.infrastructure.settings import EXCEL_FILENAME, TENANTS_ROOT


def sanitize_tenant_key(tenant_key: str) -> str:
    segment = tenant_key.strip().lower()
    segment = re.sub(r"[^a-z0-9._-]+", "_", segment)
    segment = segment.strip("._-") or "tenant"
    return segment[:200]


def tenant_data_dir(tenant_key: str) -> Path:
    return TENANTS_ROOT / sanitize_tenant_key(tenant_key)


def tenant_excel_path(tenant_key: str) -> Path:
    return tenant_data_dir(tenant_key) / EXCEL_FILENAME
