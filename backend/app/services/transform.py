"""Cleaning-transformation engine.

Each operation is a pure function DataFrame -> DataFrame. Steps are validated by
dry-running them against the current data before being persisted; the canonical
current data is always the original replayed through all stored steps.
"""
from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import pandas.api.types as pdt

from app.services.profile import iqr_bounds


class TransformError(Exception):
    """Raised when a transformation is invalid or fails (-> HTTP 400)."""


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise TransformError(f"Unknown column(s): {', '.join(missing)}")


def _drop_duplicates(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    subset = p.get("subset")
    if subset:
        _require_columns(df, subset)
    return df.drop_duplicates(subset=subset).reset_index(drop=True)


def _drop_missing_rows(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    how = p.get("how", "any")
    if how not in ("any", "all"):
        raise TransformError("`how` must be 'any' or 'all'.")
    subset = p.get("subset")
    if subset:
        _require_columns(df, subset)
    return df.dropna(how=how, subset=subset).reset_index(drop=True)


def _drop_columns(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    columns = p.get("columns") or []
    if not columns:
        raise TransformError("`columns` is required.")
    _require_columns(df, columns)
    if len(columns) >= df.shape[1]:
        raise TransformError("Cannot drop every column.")
    return df.drop(columns=columns)


def _rename_columns(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    mapping = p.get("mapping") or {}
    if not mapping:
        raise TransformError("`mapping` is required.")
    _require_columns(df, list(mapping.keys()))
    return df.rename(columns={str(k): str(v) for k, v in mapping.items()})


def _impute_missing(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    column = p.get("column")
    strategy = p.get("strategy")
    if not column:
        raise TransformError("`column` is required.")
    _require_columns(df, [column])
    series = df[column]

    if strategy in ("mean", "median"):
        if not pdt.is_numeric_dtype(series):
            raise TransformError(f"'{strategy}' imputation requires a numeric column.")
        fill = series.mean() if strategy == "mean" else series.median()
    elif strategy == "mode":
        modes = series.mode(dropna=True)
        if modes.empty:
            raise TransformError("Column has no non-missing values to derive a mode.")
        fill = modes.iloc[0]
    elif strategy == "constant":
        if "value" not in p:
            raise TransformError("`value` is required for constant imputation.")
        fill = p["value"]
    else:
        raise TransformError("`strategy` must be mean, median, mode, or constant.")

    df = df.copy()
    df[column] = series.fillna(fill)
    return df


def _cast_type(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    column = p.get("column")
    to = p.get("to")
    if not column:
        raise TransformError("`column` is required.")
    _require_columns(df, [column])
    df = df.copy()
    series = df[column]

    try:
        if to == "integer":
            df[column] = pd.to_numeric(series, errors="raise").astype("Int64")
        elif to == "float":
            df[column] = pd.to_numeric(series, errors="raise").astype("float64")
        elif to == "string":
            df[column] = series.astype("string")
        elif to == "boolean":
            mapping = {
                "true": True, "false": False, "yes": True, "no": False,
                "1": True, "0": False, "t": True, "f": False,
                "y": True, "n": False,
            }
            df[column] = (
                series.astype(str).str.strip().str.lower().map(mapping).astype("boolean")
            )
            if df[column].isna().sum() > series.isna().sum():
                raise TransformError("Some values could not be interpreted as boolean.")
        elif to == "datetime":
            df[column] = pd.to_datetime(series, errors="raise", format="mixed")
        elif to == "category":
            df[column] = series.astype("category")
        else:
            raise TransformError(f"Unsupported target type '{to}'.")
    except TransformError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface cast failure to the user
        raise TransformError(f"Could not cast '{column}' to {to}: {exc}") from exc
    return df


def _handle_outliers(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    column = p.get("column")
    method = p.get("method", "clip")
    factor = float(p.get("factor", 1.5))
    if not column:
        raise TransformError("`column` is required.")
    _require_columns(df, [column])
    series = df[column]
    if not pdt.is_numeric_dtype(series):
        raise TransformError("Outlier handling requires a numeric column.")

    low, high = iqr_bounds(series.dropna(), factor)
    df = df.copy()
    if method == "clip":
        df[column] = series.clip(low, high)
        return df
    if method == "remove":
        keep = series.isna() | ((series >= low) & (series <= high))
        return df[keep].reset_index(drop=True)
    raise TransformError("`method` must be 'clip' or 'remove'.")


_OPS: dict[str, Callable[[pd.DataFrame, dict], pd.DataFrame]] = {
    "drop_duplicates": _drop_duplicates,
    "drop_missing_rows": _drop_missing_rows,
    "drop_columns": _drop_columns,
    "rename_columns": _rename_columns,
    "impute_missing": _impute_missing,
    "cast_type": _cast_type,
    "handle_outliers": _handle_outliers,
}

OPERATIONS = tuple(_OPS)


def apply_step(df: pd.DataFrame, operation: str, params: dict[str, Any]) -> pd.DataFrame:
    fn = _OPS.get(operation)
    if fn is None:
        raise TransformError(f"Unknown operation '{operation}'.")
    return fn(df, params or {})


def replay(df: pd.DataFrame, steps: list[tuple[str, dict]]) -> pd.DataFrame:
    for operation, params in steps:
        df = apply_step(df, operation, params)
    return df
