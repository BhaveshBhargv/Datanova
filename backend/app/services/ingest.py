"""Parse uploaded files into DataFrames and persist dataset artifacts.

Kept free of database/session concerns: routes orchestrate persistence via CRUD;
this module handles parsing, schema inference, Parquet storage, and previews.
"""
from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

import pandas as pd
import pandas.api.types as pdt

from app.core.config import settings
from app.core.storage import storage

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}
MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


class IngestError(Exception):
    """Raised when an upload cannot be validated or parsed (-> HTTP 400)."""


def _dtype_label(series: pd.Series) -> str:
    if pdt.is_bool_dtype(series):
        return "boolean"
    if pdt.is_integer_dtype(series):
        return "integer"
    if pdt.is_float_dtype(series):
        return "float"
    if pdt.is_datetime64_any_dtype(series):
        return "datetime"
    if isinstance(series.dtype, pd.CategoricalDtype):
        return "categorical"
    return "string"


def parse_upload(filename: str, raw: bytes) -> tuple[pd.DataFrame, str]:
    """Validate and parse an uploaded file into a DataFrame + format label."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise IngestError(
            f"Unsupported file type '{ext or filename}'. Upload a .csv or .xlsx file."
        )
    if not raw:
        raise IngestError("The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise IngestError(
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB upload limit."
        )
    try:
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(raw))
        else:
            df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
    except Exception as exc:  # noqa: BLE001 - surface parse failure to the user
        raise IngestError(f"Could not parse the file: {exc}") from exc

    if df.shape[0] == 0 or df.shape[1] == 0:
        raise IngestError("The file contains no rows or no columns.")

    # Parquet/JSON require string column names.
    df.columns = [str(c) for c in df.columns]
    return df, ext.lstrip(".")


def column_schema(df: pd.DataFrame) -> list[dict]:
    return [
        {
            "name": col,
            "dtype": _dtype_label(df[col]),
            "nullable": bool(df[col].isna().any()),
        }
        for col in df.columns
    ]


def parquet_rel_path(owner_id: uuid.UUID, dataset_id: uuid.UUID) -> str:
    return f"{owner_id}/{dataset_id}.parquet"


def original_rel_path(owner_id: uuid.UUID, dataset_id: uuid.UUID, fmt: str) -> str:
    return f"{owner_id}/{dataset_id}.{fmt}"


def write_parquet(rel_path: str, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, engine="pyarrow", index=False)
    storage.write(rel_path, buf.getvalue())


def read_parquet(rel_path: str) -> pd.DataFrame:
    return pd.read_parquet(io.BytesIO(storage.read(rel_path)), engine="pyarrow")


def preview(rel_path: str, rows: int) -> tuple[list[str], list[dict]]:
    df = read_parquet(rel_path).head(rows)
    # to_json handles NaN -> null and dates -> ISO strings safely.
    records = json.loads(df.to_json(orient="records", date_format="iso"))
    return list(df.columns), records
