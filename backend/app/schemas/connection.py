"""Pydantic schemas for external database connections."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Dialect = Literal["postgresql", "mysql", "sqlite"]


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    dialect: Dialect
    database: str = Field(min_length=1, max_length=512)
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def _require_host_for_servers(self):
        # sqlite uses a local file path in `database`; server dialects need a host.
        if self.dialect in ("postgresql", "mysql") and not self.host:
            raise ValueError(f"host is required for {self.dialect} connections")
        return self


class ConnectionRead(BaseModel):
    """Connection details WITHOUT the password."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    dialect: str
    host: str | None
    port: int | None
    database: str
    username: str | None
    created_at: datetime


class ConnectionTestResult(BaseModel):
    ok: bool
    message: str


class TableList(BaseModel):
    tables: list[str]


class ImportRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    table: str | None = None
    query: str | None = None

    @model_validator(mode="after")
    def _one_source(self):
        if bool(self.table) == bool(self.query):
            raise ValueError("Provide exactly one of `table` or `query`.")
        return self
