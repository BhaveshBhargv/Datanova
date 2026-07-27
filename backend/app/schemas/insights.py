"""Pydantic schemas for insights & recommendations."""
from typing import Literal

from pydantic import BaseModel


class Insight(BaseModel):
    category: str
    severity: Literal["critical", "warning", "info"]
    title: str
    detail: str
    recommendation: str | None = None


class InsightsResponse(BaseModel):
    total: int
    counts: dict[str, int]
    insights: list[Insight]
