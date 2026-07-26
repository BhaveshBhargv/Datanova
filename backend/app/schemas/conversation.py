"""Pydantic schemas for conversations and messages."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="Chat", max_length=255)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    title: str
    created_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    sql: str | None = None
    result_columns: list[str] | None = None
    result_rows: list[dict[str, Any]] | None = None
    error: str | None = None
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead] = []
