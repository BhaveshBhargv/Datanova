"""Pydantic schemas for SHAP model explanations."""
from typing import Any

from pydantic import BaseModel, Field


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class ImportanceResponse(BaseModel):
    problem_type: str
    target: str
    sample_size: int
    importance: list[FeatureImportance]


class PredictionExplainRequest(BaseModel):
    index: int = Field(ge=0)


class Contribution(BaseModel):
    feature: str
    value: Any
    contribution: float


class PredictionExplainResponse(BaseModel):
    index: int
    prediction: Any
    predicted_label: Any | None = None
    proba: dict[str, float] | None = None
    base_value: float
    contributions: list[Contribution]
