"""Repositorio Excel — carga y escritura del archivo de muestras.

Optimizaciones:
- Snapshot Parquet (`.cache/data_flota.parquet`) para acelerar el boot:
  leer XLSX demora ~1–3 s; leer Parquet demora ~10–50 ms. Se regenera
  automáticamente si el XLSX es más nuevo.
- Append incremental: al registrar una muestra nueva, no invalidamos todo
  el DF en memoria — concatenamos la fila al cache y refrescamos Parquet.
  Eso evita re-leer el XLSX tras cada POST.
- `dataframe()` devuelve una referencia read-only al DF (no copy). Los
  repositorios sólo hacen filtros/groupby, no mutaciones.
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from openpyxl import load_workbook

from src.application import IEquipoRepository, IMuestraRepository
from src.domain import Equipo, EstadoEquipo, Muestra
from src.infrastructure.settings import (
    EXCEL_PATH,
    EXCEL_SHEET,
    VARIABLES_ANALITICAS,
)

logger = logging.getLogger("oilmine.excel")


# ----------------------------------------------------------------------
# Snapshot Parquet
# ----------------------------------------------------------------------
PARQUET_CACHE_DIR = EXCEL_PATH.parent / ".cache"
PARQUET_PATH: Path = PARQUET_CACHE_DIR / "data_flota.parquet"


def _parquet_is_fresh() -> bool:
    """True si el Parquet existe y es más nuevo que el XLSX."""
    if not PARQUET_PATH.exists() or not EXCEL_PATH.exists():
        return False
    return PARQUET_PATH.stat().st_mtime >= EXCEL_PATH.stat().st_mtime


def _normalize_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """Coacciona columnas `object` mixtas a string para que Parquet las acepte.

    El XLSX tiene columnas "extra" que no usamos en el modelo (p.ej.
    'Viscosidad a 40 °C cSt' con valores '-' mezclados con números). Pyarrow
    exige un solo tipo por columna, así que las estandarizamos a string.
    No tocamos columnas ya tipadas (int/float/datetime) ni las variables
    analíticas que ya pasaron por `pd.to_numeric`.
    """
    df2 = df.copy()
    for col in df2.columns:
        if df2[col].dtype == "object" and col not in {"Equipo", "Estado"}:
            # Muestra el tipo de los primeros no-null para decidir.
            try:
                df2[col] = df2[col].astype("string")
            except Exception:
                df2[col] = df2[col].map(
                    lambda x: None if pd.isna(x) else str(x)
                )
    return df2


def _write_parquet(df: pd.DataFrame) -> None:
    """Guarda `df` como Parquet; silencioso si falla (no debe romper la app)."""
    try:
        PARQUET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _normalize_for_parquet(df).to_parquet(PARQUET_PATH, index=False)
        logger.info(f"Snapshot Parquet guardado: {PARQUET_PATH.name} ({len(df)} filas)")
    except Exception as e:
        logger.warning(f"No se pudo escribir snapshot Parquet: {e}")


# ======================================================================
# ExcelManager — singleton thread-safe
# ======================================================================
class ExcelManager:
    """Singleton: lee Excel/Parquet una vez en memoria, apendiza incremental."""

    _instance: Optional["ExcelManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._io_lock = threading.Lock()
                    obj._df: Optional[pd.DataFrame] = None
                    obj._header: Optional[List[str]] = None
                    cls._instance = obj
        return cls._instance

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def _load(self) -> None:
        """Carga el DF en memoria. Prefiere Parquet si está fresco."""
        df: Optional[pd.DataFrame] = None

        if _parquet_is_fresh():
            try:
                df = pd.read_parquet(PARQUET_PATH)
                logger.info(
                    f"Datos cargados desde Parquet ({len(df)} filas) — skip XLSX"
                )
            except Exception as e:
                logger.warning(f"Parquet corrupto, recurro al XLSX: {e}")
                df = None

        if df is None:
            df = pd.read_excel(EXCEL_PATH, sheet_name=EXCEL_SHEET)
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
            df["Hora_Producto"] = pd.to_numeric(df["Hora_Producto"], errors="coerce")
            for col in VARIABLES_ANALITICAS:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            # Snapshot para próximos arranques.
            _write_parquet(df)

        # Orden cronológico: primero por fecha (señal temporal real),
        # luego Hora_Producto como desempate (dos muestras del mismo día
        # dentro de un ciclo). Así una muestra recién registrada siempre
        # queda como "última" aunque su Hora_Producto sea menor (p.ej.
        # después de un cambio de aceite).
        df = df.sort_values(["Equipo", "Fecha", "Hora_Producto"]).reset_index(drop=True)
        self._df = df
        self._header = list(df.columns)

    def _ensure_loaded(self) -> None:
        if self._df is None:
            self._load()

    def dataframe(self) -> pd.DataFrame:
        """Devuelve el DF cacheado (sin copy — usarlo read-only)."""
        with self._io_lock:
            self._ensure_loaded()
            return self._df  # type: ignore[return-value]

    def preload(self) -> None:
        """Fuerza la carga del DF en memoria. Llamar al arranque."""
        with self._io_lock:
            self._ensure_loaded()

    def rebuild_parquet(self) -> None:
        """Regenera el Parquet desde el XLSX. Útil si el snapshot queda stale."""
        with self._io_lock:
            self._df = None
            self._load()

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------
    def append_row(self, row: Dict[str, object]) -> None:
        """Añade una fila al Excel y al DF en memoria sin invalidar el cache.

        Las columnas no presentes en `row` quedan vacías.
        """
        with self._io_lock:
            # 1. Persistir en Excel (openpyxl preserva formato original)
            wb = load_workbook(EXCEL_PATH)
            ws = wb[EXCEL_SHEET]
            header = [c.value for c in ws[1]]
            new_row = [row.get(col, None) for col in header]
            ws.append(new_row)
            wb.save(EXCEL_PATH)
            wb.close()

            # 2. Append incremental al DF en memoria (si ya estaba cargado)
            if self._df is not None:
                new_df_row = {col: row.get(col, None) for col in self._df.columns}
                # Coerción de tipos consistente con _load()
                if "Fecha" in new_df_row and new_df_row["Fecha"] is not None:
                    new_df_row["Fecha"] = pd.to_datetime(
                        new_df_row["Fecha"], errors="coerce"
                    )
                if "Hora_Producto" in new_df_row:
                    new_df_row["Hora_Producto"] = pd.to_numeric(
                        new_df_row["Hora_Producto"], errors="coerce"
                    )
                for col in VARIABLES_ANALITICAS:
                    if col in new_df_row:
                        new_df_row[col] = pd.to_numeric(
                            new_df_row[col], errors="coerce"
                        )
                self._df = pd.concat(
                    [self._df, pd.DataFrame([new_df_row])],
                    ignore_index=True,
                )
                self._df = self._df.sort_values(
                    ["Equipo", "Fecha", "Hora_Producto"]
                ).reset_index(drop=True)

                # 3. Refrescar Parquet en background (no bloquear el append)
                try:
                    _write_parquet(self._df)
                except Exception:
                    pass
            else:
                # Aún no se había cargado: lazy-load en la próxima lectura.
                self._df = None


# ======================================================================
# Repositorios
# ======================================================================
class ExcelEquipoRepository(IEquipoRepository):
    def __init__(self, manager: Optional[ExcelManager] = None) -> None:
        self.manager = manager or ExcelManager()

    # ------------------------------------------------------------------
    def listar_ids(self) -> List[str]:
        df = self.manager.dataframe()
        return sorted(df["Equipo"].dropna().unique().tolist())

    # ------------------------------------------------------------------
    def obtener(self, equipo_id: str) -> Equipo:
        df = self.manager.dataframe()
        grp = (
            df[df["Equipo"] == equipo_id]
            .sort_values(["Fecha", "Hora_Producto"])
            .reset_index(drop=True)
        )
        if grp.empty:
            raise ValueError(f"Equipo '{equipo_id}' no existe en el Excel")
        return self._build_equipo(equipo_id, grp)

    # ------------------------------------------------------------------
    def obtener_todos(self) -> List[Equipo]:
        df = self.manager.dataframe()
        equipos: List[Equipo] = []
        for equipo_id, grp in df.groupby("Equipo"):
            grp = grp.sort_values(["Fecha", "Hora_Producto"]).reset_index(drop=True)
            equipos.append(self._build_equipo(str(equipo_id), grp))
        return equipos

    # ------------------------------------------------------------------
    def _build_equipo(self, equipo_id: str, grp: pd.DataFrame) -> Equipo:
        muestras: List[Muestra] = []
        for _, r in grp.iterrows():
            estado_raw = r.get("Estado")
            try:
                estado = EstadoEquipo(estado_raw) if pd.notna(estado_raw) else None
            except ValueError:
                estado = None

            variables: Dict[str, float] = {}
            for v in VARIABLES_ANALITICAS:
                val = r.get(v)
                if pd.notna(val):
                    variables[v] = float(val)
                else:
                    variables[v] = float("nan")

            hora = r.get("Hora_Producto")
            if pd.isna(hora):
                continue
            fecha_val = r.get("Fecha")
            fecha_obj = (
                fecha_val.date() if isinstance(fecha_val, (pd.Timestamp, datetime)) else None
            )

            muestras.append(
                Muestra(
                    equipo=equipo_id,
                    fecha=fecha_obj,
                    hora_producto=float(hora),
                    estado=estado,
                    variables=variables,
                )
            )
        return Equipo(id=equipo_id, muestras=muestras)


class ExcelMuestraRepository(IMuestraRepository):
    def __init__(self, manager: Optional[ExcelManager] = None) -> None:
        self.manager = manager or ExcelManager()

    def registrar(self, muestra: Muestra) -> None:
        fecha = muestra.fecha
        if isinstance(fecha, date) and not isinstance(fecha, datetime):
            fecha = datetime.combine(fecha, datetime.min.time())

        row = {
            "Equipo": muestra.equipo,
            "Fecha": fecha,
            "Hora_Producto": muestra.hora_producto,
        }
        if muestra.estado is not None:
            row["Estado"] = muestra.estado.value
        row.update(muestra.variables)
        self.manager.append_row(row)
