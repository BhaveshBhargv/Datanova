"""Automated data-quality profiling for a DataFrame.

Produces dataset-level and per-column statistics, IQR-based outlier counts, and
type suggestions for string columns that look numeric/datetime/boolean/categorical.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pandas.api.types as pdt

_BOOL_TOKENS = {"true", "false", "yes", "no", "0", "1", "t", "f", "y", "n"}


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


def _num(value: Any) -> float | None:
    """Convert a numpy scalar to a JSON-safe float (None for NaN)."""
    if value is None:
        return None
    f = float(value)
    return None if np.isnan(f) else f


def iqr_bounds(series: pd.Series, factor: float = 1.5) -> tuple[float, float]:
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return q1 - factor * iqr, q3 + factor * iqr


def _outlier_count(series: pd.Series) -> int:
    clean = series.dropna()
    if clean.empty:
        return 0
    low, high = iqr_bounds(clean)
    return int(((clean < low) | (clean > high)).sum())


def _suggest_type(series: pd.Series) -> str | None:
    """Suggest a better type for an object/string column, or None."""
    if not (pdt.is_object_dtype(series) or isinstance(series.dtype, pd.StringDtype)):
        return None
    non_null = series.dropna().astype(str).str.strip()
    if non_null.empty:
        return None

    tokens = set(non_null.str.lower().unique())
    if tokens <= _BOOL_TOKENS:
        return "boolean"

    numeric_ratio = pd.to_numeric(non_null, errors="coerce").notna().mean()
    if numeric_ratio >= 0.95:
        # All-integer-looking values -> integer, else float.
        as_num = pd.to_numeric(non_null, errors="coerce").dropna()
        if (as_num == as_num.round()).all():
            return "integer"
        return "float"

    datetime_ratio = pd.to_datetime(
        non_null, errors="coerce", format="mixed"
    ).notna().mean()
    if datetime_ratio >= 0.95:
        return "datetime"

    if series.notna().sum() and series.nunique() / series.notna().sum() <= 0.5:
        return "category"
    return None


def _profile_column(series: pd.Series) -> dict:
    n = int(len(series))
    missing = int(series.isna().sum())
    profile: dict[str, Any] = {
        "name": str(series.name),
        "dtype": _dtype_label(series),
        "count": n - missing,
        "missing": missing,
        "missing_pct": round(missing / n * 100, 2) if n else 0.0,
        "unique": int(series.nunique(dropna=True)),
        "suggested_type": _suggest_type(series),
    }

    if pdt.is_numeric_dtype(series) and not pdt.is_bool_dtype(series):
        clean = series.dropna()
        if not clean.empty:
            profile.update(
                min=_num(clean.min()),
                max=_num(clean.max()),
                mean=round(float(clean.mean()), 4),
                median=_num(clean.median()),
                std=round(float(clean.std()), 4) if len(clean) > 1 else 0.0,
                q1=_num(clean.quantile(0.25)),
                q3=_num(clean.quantile(0.75)),
                outliers=_outlier_count(clean),
            )
    elif pdt.is_datetime64_any_dtype(series):
        clean = series.dropna()
        if not clean.empty:
            profile.update(
                min=clean.min().isoformat(),
                max=clean.max().isoformat(),
            )
    else:
        counts = series.value_counts(dropna=True).head(5)
        profile["top_values"] = [
            {"value": str(idx), "count": int(cnt)} for idx, cnt in counts.items()
        ]

    return profile


def _quality_score(
    n_rows: int,
    n_cols: int,
    missing_cells: int,
    duplicate_rows: int,
    total_outliers: int,
    numeric_cells: int,
) -> float:
    if n_rows == 0 or n_cols == 0:
        return 0.0
    missing_pct = missing_cells / (n_rows * n_cols) * 100
    dup_pct = duplicate_rows / n_rows * 100
    outlier_pct = (total_outliers / numeric_cells * 100) if numeric_cells else 0.0
    score = 100 - 0.5 * missing_pct - 0.5 * dup_pct - 0.3 * outlier_pct
    return round(max(0.0, min(100.0, score)), 1)


def profile_dataframe(df: pd.DataFrame) -> dict:
    n_rows, n_cols = int(df.shape[0]), int(df.shape[1])
    columns = [_profile_column(df[c]) for c in df.columns]

    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    total_outliers = sum(c.get("outliers", 0) or 0 for c in columns)
    numeric_cells = sum(
        c["count"] for c in columns if "outliers" in c
    )

    return {
        "n_rows": n_rows,
        "n_columns": n_cols,
        "duplicate_rows": duplicate_rows,
        "missing_cells": missing_cells,
        "missing_pct": round(missing_cells / (n_rows * n_cols) * 100, 2)
        if n_rows and n_cols
        else 0.0,
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
        "quality_score": _quality_score(
            n_rows, n_cols, missing_cells, duplicate_rows, total_outliers, numeric_cells
        ),
        "columns": columns,
    }
