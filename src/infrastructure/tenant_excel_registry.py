"""Registry thread-safe de ``ExcelManager`` por tenant."""
from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Dict

from src.infrastructure.excel_repository import ExcelManager
from src.infrastructure.settings import EXCEL_PATH, EXCEL_SHEET
from src.infrastructure.tenant_paths import sanitize_tenant_key, tenant_excel_path


class TenantExcelRegistry:
    """Mantiene una ``ExcelManager`` por ``tenant_key`` (dominio email)."""

    _instances: Dict[str, ExcelManager] = {}
    _lock = threading.Lock()

    @classmethod
    def ensure_tenant_dataset(cls, tenant_key: str) -> Path:
        """Copia el XLSX maestro si el tenant aún no tiene dataset."""
        dst = tenant_excel_path(tenant_key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(EXCEL_PATH, dst)
        return dst

    @classmethod
    def get_manager(cls, tenant_key: str) -> ExcelManager:
        """Devuelve (o crea) el manager para este tenant."""
        cls.ensure_tenant_dataset(tenant_key)
        sk = sanitize_tenant_key(tenant_key)
        with cls._lock:
            if sk not in cls._instances:
                cls._instances[sk] = ExcelManager(
                    tenant_excel_path(tenant_key),
                    EXCEL_SHEET,
                )
            return cls._instances[sk]

    @classmethod
    def preload_tenant(cls, tenant_key: str) -> None:
        cls.get_manager(tenant_key).preload()
