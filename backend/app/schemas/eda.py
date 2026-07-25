"""Pydantic schemas for EDA summaries and AI explanations."""
from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.chart import ChartSpec


class Correlations(BaseModel):
    columns: list[str]
    matrix: list[list[Any]]


class RecommendedChart(BaseModel):
    type: str
    reason: str
    column: str | None = None
    x: str | None = None
    y: str | None = None


class EdaSummary(BaseModel):
    numeric: dict[str, dict[str, Any]]
    correlations: Correlations
    recommended_charts: list[RecommendedChart]


class ExplainRequest(BaseModel):
    kind: Literal["overview", "chart"]
    spec: ChartSpec | None = None


class ExplainResponse(BaseModel):
    text: str
    source: Literal["llm", "fallback"]
