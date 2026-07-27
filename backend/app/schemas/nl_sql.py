"""Pydantic schemas for NL->SQL over connected databases."""
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    name: str
    type: str


class TableSchema(BaseModel):
    table: str
    columns: list[ColumnInfo]


class SchemaResponse(BaseModel):
    tables: list[TableSchema]


class NLQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class NLQueryResponse(BaseModel):
    sql: str | None = None
    columns: list[str] | None = None
    rows: list[dict[str, Any]] | None = None
    row_count: int | None = None
    plan: list[str] = []
    optimization_notes: list[str] = []
    explanation: str
    source: Literal["llm", "fallback"] | None = None
    error: str | None = None


class QueryHistoryItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    question: str
    sql: str | None = None
    explanation: str | None = None
    source: str | None = None
    row_count: int | None = None
    error: str | None = None
    created_at: datetime
