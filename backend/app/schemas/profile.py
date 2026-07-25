"""Pydantic schemas for the data-quality profile."""
from typing import Any

from pydantic import BaseModel


class TopValue(BaseModel):
    value: Any
    count: int


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    count: int
    missing: int
    missing_pct: float
    unique: int
    suggested_type: str | None = None

    # Numeric-only
    min: Any | None = None
    max: Any | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    q1: float | None = None
    q3: float | None = None
    outliers: int | None = None

    # Categorical/string-only
    top_values: list[TopValue] | None = None


class DatasetProfile(BaseModel):
    n_rows: int
    n_columns: int
    duplicate_rows: int
    missing_cells: int
    missing_pct: float
    memory_bytes: int
    quality_score: float
    columns: list[ColumnProfile]
