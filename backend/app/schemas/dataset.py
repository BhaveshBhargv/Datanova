"""Pydantic schemas for datasets."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    nullable: bool


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    file_format: str | None
    n_rows: int
    n_columns: int
    size_bytes: int | None
    columns: list[ColumnInfo]
    status: str
    error: str | None
    created_at: datetime


class DatasetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class DatasetPreview(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
