"""Pydantic schemas for the analytics workspace summary."""
import uuid
from datetime import datetime

from pydantic import BaseModel


class WorkspaceCounts(BaseModel):
    datasets: int
    connections: int
    models: int
    chats: int


class RecentDataset(BaseModel):
    id: uuid.UUID
    name: str
    n_rows: int
    n_columns: int
    source_type: str
    created_at: datetime


class RecentModel(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str
    target: str
    problem_type: str
    best_model_name: str | None
    created_at: datetime | None


class RecentQuery(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    connection_name: str
    question: str
    created_at: datetime


class WorkspaceSummary(BaseModel):
    counts: WorkspaceCounts
    recent_datasets: list[RecentDataset]
    recent_models: list[RecentModel]
    recent_queries: list[RecentQuery]
