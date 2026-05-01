"""Rutas para validar e importar dataset de una organización."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from src.infrastructure.data_import import (
    OPTIONAL_HEADERS,
    required_headers,
    validate_dataset,
    write_dataset_excel,
)
from src.infrastructure.tenant_excel_registry import TenantExcelRegistry
from src.infrastructure.tenant_paths import tenant_excel_path
from src.interfaces.api import dependencies as deps
from src.interfaces.api.schemas import (
    DatasetPreviewResponse,
    DatasetStatusResponse,
    DatasetValidationResponse,
)
from src.interfaces.api.user_context import UserContext

router = APIRouter(prefix="/org/dataset", tags=["dataset"])


async def _upload_to_temp(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "dataset.xlsx").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await upload.read())
        return Path(tmp.name)


def _status_for(uc: UserContext) -> DatasetStatusResponse:
    headers = required_headers()
    if not TenantExcelRegistry.has_tenant_dataset(uc.tenant_key):
        return DatasetStatusResponse(
            loaded=False,
            tenant_key=uc.tenant_key,
            org_name=uc.org_name,
            required_headers=headers,
            optional_headers=OPTIONAL_HEADERS,
        )
    manager = TenantExcelRegistry.get_manager(uc.tenant_key)
    df = manager.dataframe()
    return DatasetStatusResponse(
        loaded=True,
        tenant_key=uc.tenant_key,
        org_name=uc.org_name,
        total_rows=int(len(df)),
        total_equipos=int(df["Equipo"].nunique()) if "Equipo" in df.columns else 0,
        required_headers=headers,
        optional_headers=OPTIONAL_HEADERS,
    )


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 4)
    return value


@router.get("/status", response_model=DatasetStatusResponse)
def dataset_status(uc: UserContext = Depends(deps.require_auth)) -> DatasetStatusResponse:
    return _status_for(uc)


@router.get("/template", response_model=DatasetStatusResponse)
def dataset_template(uc: UserContext = Depends(deps.require_auth)) -> DatasetStatusResponse:
    return _status_for(uc)


@router.get("/preview", response_model=DatasetPreviewResponse)
def dataset_preview(
    max_rows: int = Query(default=8, ge=1, le=50),
    uc: UserContext = Depends(deps.require_auth),
) -> DatasetPreviewResponse:
    if not TenantExcelRegistry.has_tenant_dataset(uc.tenant_key):
        return DatasetPreviewResponse(
            loaded=False,
            tenant_key=uc.tenant_key,
            org_name=uc.org_name,
        )

    df = TenantExcelRegistry.get_manager(uc.tenant_key).dataframe()
    preferred = [*required_headers(), "Producto", "Codigo"]
    columns = [col for col in preferred if col in df.columns]
    if not columns:
        columns = list(df.columns[:12])
    rows = [
        {col: _json_value(row[col]) for col in columns}
        for _, row in df[columns].head(max_rows).iterrows()
    ]
    return DatasetPreviewResponse(
        loaded=True,
        tenant_key=uc.tenant_key,
        org_name=uc.org_name,
        total_rows=int(len(df)),
        total_equipos=int(df["Equipo"].nunique()) if "Equipo" in df.columns else 0,
        columns=columns,
        rows=rows,
    )


@router.get("/download")
def dataset_download(
    uc: UserContext = Depends(deps.require_auth),
) -> FileResponse:
    if not TenantExcelRegistry.has_tenant_dataset(uc.tenant_key):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="La organización todavía no tiene dataset cargado",
        )

    path = tenant_excel_path(uc.tenant_key)
    filename = f"{uc.tenant_key}_dataset.xlsx"
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/validate", response_model=DatasetValidationResponse)
async def validate_upload(
    file: UploadFile = File(...),
    _: UserContext = Depends(deps.require_admin),
) -> DatasetValidationResponse:
    path = await _upload_to_temp(file)
    try:
        validation, _ = validate_dataset(path)
        return DatasetValidationResponse(**validation.as_dict())
    finally:
        path.unlink(missing_ok=True)


@router.post("/import", response_model=DatasetStatusResponse)
async def import_upload(
    confirm_replace: bool = Query(default=False),
    file: UploadFile = File(...),
    uc: UserContext = Depends(deps.require_admin),
) -> DatasetStatusResponse:
    if TenantExcelRegistry.has_tenant_dataset(uc.tenant_key) and not confirm_replace:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                "Esta organización ya tiene dataset cargado. Confirma el reemplazo "
                "para sobrescribir toda la data actual."
            ),
        )
    path = await _upload_to_temp(file)
    normalized_path = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name)
    try:
        validation, df = validate_dataset(path)
        if not validation.ok or df is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=validation.as_dict(),
            )
        write_dataset_excel(df, normalized_path)
        TenantExcelRegistry.save_tenant_dataset(uc.tenant_key, normalized_path)
        deps.get_prediction_cache().invalidate_prefix(f"t:{uc.tenant_key}:")
        return _status_for(uc)
    finally:
        path.unlink(missing_ok=True)
        normalized_path.unlink(missing_ok=True)
