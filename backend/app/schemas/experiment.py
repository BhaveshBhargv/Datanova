"""Pydantic schemas for AutoML experiments."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExperimentCreate(BaseModel):
    target: str = Field(min_length=1)
    features: list[str] | None = None
    test_size: float = Field(default=0.2, ge=0.1, le=0.5)


class ModelResult(BaseModel):
    model: str
    metrics: dict[str, Any]


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    target_column: str
    feature_columns: list[str]
    problem_type: str
    status: str
    test_size: float
    results: list[ModelResult] | None = None
    best_model_name: str | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
