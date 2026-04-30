"""Registry thread-safe de ExcelManager por tenant."""
from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Dict

from src.infrastructure.excel_repository import ExcelManager
from src.infrastructure.settings import EXCEL_PATH, EXCEL_SHEET
from src.infrastructure.tenant_paths import sanitize_tenant_key, tenant_excel_path


class TenantExcelRegistry:
    """Mantiene un ExcelManager por tenant aislado."""

    _instances: Dict[str, ExcelManager] = {}
    _lock = threading.Lock()

    @classmethod
    def ensure_tenant_dataset(cls, tenant_key: str) -> Path:
        dst = tenant_excel_path(tenant_key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(EXCEL_PATH, dst)
        return dst

    @classmethod
    def clone_tenant_dataset(cls, source_tenant: str, target_tenant: str) -> Path:
        dst = tenant_excel_path(target_tenant)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            return dst

        src = tenant_excel_path(source_tenant)
        shutil.copy2(src if src.exists() else EXCEL_PATH, dst)
        return dst

    @classmethod
    def get_manager(cls, tenant_key: str) -> ExcelManager:
        cls.ensure_tenant_dataset(tenant_key)
        key = sanitize_tenant_key(tenant_key)
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = ExcelManager(
                    tenant_excel_path(tenant_key),
                    EXCEL_SHEET,
                )
            return cls._instances[key]

    @classmethod
    def preload_tenant(cls, tenant_key: str) -> None:
        cls.get_manager(tenant_key).preload()
