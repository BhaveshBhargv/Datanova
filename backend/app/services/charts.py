"""Compute ECharts-ready aggregates for a DataFrame.

Each chart type returns a consistent dict shape so the frontend can build an
ECharts option generically. Heavy data stays server-side; only summaries are sent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.api.types as pdt

SCATTER_SAMPLE = 2000
CHART_TYPES = (
    "histogram",
    "bar",
    "pie",
    "box",
    "scatter",
    "correlation_heatmap",
    "line",
)


class ChartError(Exception):
    """Raised for an invalid chart specification (-> HTTP 400)."""


def _require(df: pd.DataFrame, col: str | None) -> str:
    if not col:
        raise ChartError("This chart requires a column.")
    if col not in df.columns:
        raise ChartError(f"Unknown column '{col}'.")
    return col


def _require_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    s = df[col]
    if not pdt.is_numeric_dtype(s) or pdt.is_bool_dtype(s):
        raise ChartError(f"Column '{col}' is not numeric.")
    return s


def _num(v) -> float | None:
    if v is None:
        return None
    f = float(v)
    return None if np.isnan(f) else f


def histogram(df: pd.DataFrame, spec: dict) -> dict:
    col = _require(df, spec.get("column"))
    series = _require_numeric(df, col).dropna()
    bins = int(spec.get("bins") or 20)
    if series.empty:
        raise ChartError(f"Column '{col}' has no numeric values.")
    counts, edges = np.histogram(series, bins=bins)
    labels = [f"{edges[i]:.2f}–{edges[i + 1]:.2f}" for i in range(len(edges) - 1)]
    return {
        "type": "histogram",
        "title": f"Distribution of {col}",
        "x_label": col,
        "y_label": "Count",
        "categories": labels,
        "series": [{"name": col, "data": [int(c) for c in counts]}],
        "extra": {},
    }


def bar(df: pd.DataFrame, spec: dict) -> dict:
    col = _require(df, spec.get("column"))
    top_n = int(spec.get("top_n") or 10)
    counts = df[col].value_counts(dropna=True).head(top_n)
    return {
        "type": "bar",
        "title": f"Frequency of {col}",
        "x_label": col,
        "y_label": "Count",
        "categories": [str(i) for i in counts.index],
        "series": [{"name": "Count", "data": [int(v) for v in counts.values]}],
        "extra": {},
    }


def pie(df: pd.DataFrame, spec: dict) -> dict:
    col = _require(df, spec.get("column"))
    top_n = int(spec.get("top_n") or 8)
    counts = df[col].value_counts(dropna=True).head(top_n)
    return {
        "type": "pie",
        "title": f"Composition of {col}",
        "categories": None,
        "series": [
            {
                "name": col,
                "data": [
                    {"name": str(i), "value": int(v)} for i, v in counts.items()
                ],
            }
        ],
        "extra": {},
    }


def box(df: pd.DataFrame, spec: dict) -> dict:
    if spec.get("column"):
        cols = [_require(df, spec["column"])]
    else:
        cols = [
            c
            for c in df.columns
            if pdt.is_numeric_dtype(df[c]) and not pdt.is_bool_dtype(df[c])
        ][:8]
    if not cols:
        raise ChartError("No numeric columns available for a box plot.")

    box_data, outliers = [], []
    for idx, col in enumerate(cols):
        s = _require_numeric(df, col).dropna()
        if s.empty:
            box_data.append([None] * 5)
            continue
        q1, med, q3 = s.quantile(0.25), s.median(), s.quantile(0.75)
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        inside = s[(s >= low) & (s <= high)]
        box_data.append(
            [
                _num(inside.min()),
                _num(q1),
                _num(med),
                _num(q3),
                _num(inside.max()),
            ]
        )
        for v in s[(s < low) | (s > high)]:
            outliers.append([idx, _num(v)])

    return {
        "type": "box",
        "title": "Box plot" + (f" of {cols[0]}" if len(cols) == 1 else ""),
        "x_label": None,
        "y_label": "Value",
        "categories": cols,
        "series": [{"name": "box", "data": box_data}],
        "extra": {"outliers": outliers},
    }


def scatter(df: pd.DataFrame, spec: dict) -> dict:
    x = _require(df, spec.get("x"))
    y = _require(df, spec.get("y"))
    _require_numeric(df, x)
    _require_numeric(df, y)
    sub = df[[x, y]].dropna()
    if len(sub) > SCATTER_SAMPLE:
        sub = sub.sample(SCATTER_SAMPLE, random_state=0)
    return {
        "type": "scatter",
        "title": f"{y} vs {x}",
        "x_label": x,
        "y_label": y,
        "categories": None,
        "series": [
            {
                "name": f"{y} vs {x}",
                "data": [[_num(a), _num(b)] for a, b in sub.to_numpy()],
            }
        ],
        "extra": {},
    }


def correlation_heatmap(df: pd.DataFrame, spec: dict) -> dict:
    numeric = [
        c for c in df.columns if pdt.is_numeric_dtype(df[c]) and not pdt.is_bool_dtype(df[c])
    ]
    if len(numeric) < 2:
        raise ChartError("Need at least two numeric columns for a correlation heatmap.")
    corr = df[numeric].corr(numeric_only=True).round(3)
    data = []
    for i, _ in enumerate(numeric):
        for j, _ in enumerate(numeric):
            val = corr.iat[i, j]
            data.append([i, j, None if pd.isna(val) else float(val)])
    return {
        "type": "correlation_heatmap",
        "title": "Correlation heatmap",
        "categories": numeric,
        "series": [{"name": "correlation", "data": data}],
        "extra": {"x": numeric, "y": numeric, "min": -1, "max": 1},
    }


def line(df: pd.DataFrame, spec: dict) -> dict:
    x = _require(df, spec.get("x"))
    y = _require(df, spec.get("y"))
    _require_numeric(df, y)
    sub = df[[x, y]].dropna().sort_values(x)
    if pdt.is_datetime64_any_dtype(sub[x]):
        cats = [v.isoformat() for v in sub[x]]
    else:
        cats = [str(v) for v in sub[x]]
    return {
        "type": "line",
        "title": f"{y} over {x}",
        "x_label": x,
        "y_label": y,
        "categories": cats,
        "series": [{"name": y, "data": [_num(v) for v in sub[y]]}],
        "extra": {},
    }


_BUILDERS = {
    "histogram": histogram,
    "bar": bar,
    "pie": pie,
    "box": box,
    "scatter": scatter,
    "correlation_heatmap": correlation_heatmap,
    "line": line,
}


def build(df: pd.DataFrame, spec: dict) -> dict:
    chart_type = spec.get("type")
    builder = _BUILDERS.get(chart_type)
    if builder is None:
        raise ChartError(f"Unknown chart type '{chart_type}'.")
    return builder(df, spec)
