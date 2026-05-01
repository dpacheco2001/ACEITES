"""Validación e importación controlada de datasets de laboratorio."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.infrastructure.settings import EXCEL_SHEET, VARIABLES_ANALITICAS

CORE_HEADERS = ["Equipo", "Fecha", "Hora_Producto"]
OPTIONAL_HEADERS = ["Codigo", "Producto", "Observacion", "Accion_Sugerida"]
VALID_STATES = {"NORMAL", "PRECAUCION", "CRITICO"}


@dataclass
class DatasetValidation:
    ok: bool
    total_rows: int
    total_equipos: int
    missing_headers: list[str]
    errors: list[str]
    warnings: list[str]
    headers: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total_rows": self.total_rows,
            "total_equipos": self.total_equipos,
            "missing_headers": self.missing_headers,
            "errors": self.errors,
            "warnings": self.warnings,
            "headers": self.headers,
            "required_headers": required_headers(),
            "optional_headers": OPTIONAL_HEADERS,
        }


def required_headers() -> list[str]:
    return [*CORE_HEADERS, "Estado", *VARIABLES_ANALITICAS]


def read_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        book = pd.ExcelFile(path)
        sheet = EXCEL_SHEET if EXCEL_SHEET in book.sheet_names else book.sheet_names[0]
        return pd.read_excel(path, sheet_name=sheet)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError("Formato no soportado. Usa .xlsx, .xlsm, .xls o .csv")


def validate_dataset(path: Path) -> tuple[DatasetValidation, pd.DataFrame | None]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        df = read_dataset(path)
    except Exception as e:
        validation = DatasetValidation(False, 0, 0, [], [str(e)], [], [])
        return validation, None

    headers = [str(c).strip() for c in df.columns]
    df.columns = headers
    missing = [h for h in required_headers() if h not in headers]
    if missing:
        errors.append(f"Faltan columnas obligatorias: {', '.join(missing)}")

    if df.empty:
        errors.append("El archivo no tiene filas de datos")

    if "Equipo" in df.columns:
        empty_equipment = df["Equipo"].isna() | (df["Equipo"].astype(str).str.strip() == "")
        if empty_equipment.any():
            errors.append(f"Hay {int(empty_equipment.sum())} filas sin Equipo")

    if "Fecha" in df.columns:
        parsed = pd.to_datetime(df["Fecha"], errors="coerce")
        bad = int(parsed.isna().sum())
        if bad:
            errors.append(f"Hay {bad} filas con Fecha inválida")
        df["Fecha"] = parsed

    if "Hora_Producto" in df.columns:
        parsed = pd.to_numeric(df["Hora_Producto"], errors="coerce")
        bad = int(parsed.isna().sum())
        if bad:
            errors.append(f"Columna Hora_Producto: {bad} valores no numéricos o vacíos")
        df["Hora_Producto"] = parsed

    for col in VARIABLES_ANALITICAS:
        if col not in df.columns:
            continue
        parsed = pd.to_numeric(df[col], errors="coerce")
        bad = int(parsed.isna().sum())
        if bad:
            warnings.append(f"Columna {col}: {bad} valores vacíos/no numéricos; se guardan como NaN.")
        df[col] = parsed

    if "Estado" in df.columns:
        states = df["Estado"].dropna().astype(str).str.upper().str.strip()
        invalid = sorted(set(states) - VALID_STATES)
        if invalid:
            errors.append(f"Estados inválidos: {', '.join(invalid[:8])}")
        df["Estado"] = states.reindex(df.index)

    total_rows = int(len(df))
    total_equipos = int(df["Equipo"].nunique()) if "Equipo" in df.columns else 0
    if total_equipos and total_rows:
        counts = df.groupby("Equipo").size()
        sparse = int((counts < 5).sum())
        if sparse:
            warnings.append(
                f"{sparse} equipos tienen menos de 5 muestras; el modelo baja confianza."
            )

    validation = DatasetValidation(
        ok=not errors,
        total_rows=total_rows,
        total_equipos=total_equipos,
        missing_headers=missing,
        errors=errors[:50],
        warnings=warnings,
        headers=headers,
    )
    return validation, df if validation.ok else None


def write_dataset_excel(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=EXCEL_SHEET)
