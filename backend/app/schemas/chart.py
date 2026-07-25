"""Pydantic schemas for chart specifications and computed chart data."""
from typing import Any, Literal

from pydantic import BaseModel, Field

ChartType = Literal[
    "histogram", "bar", "pie", "box", "scatter", "correlation_heatmap", "line"
]


class ChartSpec(BaseModel):
    type: ChartType
    column: str | None = None
    x: str | None = None
    y: str | None = None
    bins: int | None = Field(default=None, ge=2, le=200)
    top_n: int | None = Field(default=None, ge=1, le=50)


class ChartSeries(BaseModel):
    name: str
    data: Any


class ChartData(BaseModel):
    type: str
    title: str
    x_label: str | None = None
    y_label: str | None = None
    categories: list[Any] | None = None
    series: list[ChartSeries]
    extra: dict = {}
