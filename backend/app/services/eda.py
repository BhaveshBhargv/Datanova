"""Exploratory data analysis: numeric summaries, correlations, chart recommendations."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.api.types as pdt


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [
        c
        for c in df.columns
        if pdt.is_numeric_dtype(df[c]) and not pdt.is_bool_dtype(df[c])
    ]


def _categorical_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in df.columns:
        s = df[c]
        if pdt.is_numeric_dtype(s) or pdt.is_datetime64_any_dtype(s):
            continue
        n = int(s.notna().sum())
        if n and s.nunique(dropna=True) / n <= 0.5:
            cols.append(c)
    return cols


def _datetime_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pdt.is_datetime64_any_dtype(df[c])]


def numeric_summary(df: pd.DataFrame) -> dict:
    numeric = _numeric_columns(df)
    if not numeric:
        return {}
    desc = df[numeric].describe().replace({np.nan: None})
    return {col: desc[col].round(4).to_dict() for col in numeric}


def correlations(df: pd.DataFrame) -> dict:
    numeric = _numeric_columns(df)
    if len(numeric) < 2:
        return {"columns": [], "matrix": []}
    corr = df[numeric].corr(numeric_only=True).round(3).replace({np.nan: None})
    return {
        "columns": numeric,
        "matrix": corr.values.tolist(),
    }


def recommend_charts(df: pd.DataFrame, limit: int = 6) -> list[dict]:
    numeric = _numeric_columns(df)
    categorical = _categorical_columns(df)
    datetimes = _datetime_columns(df)
    recs: list[dict] = []

    for col in numeric[:2]:
        recs.append(
            {"type": "histogram", "column": col, "reason": f"Distribution of {col}"}
        )
    for col in categorical[:2]:
        recs.append(
            {"type": "bar", "column": col, "reason": f"Frequency of {col} categories"}
        )
    if len(numeric) >= 2:
        recs.append(
            {
                "type": "scatter",
                "x": numeric[0],
                "y": numeric[1],
                "reason": f"Relationship between {numeric[0]} and {numeric[1]}",
            }
        )
        recs.append(
            {"type": "correlation_heatmap", "reason": "Correlations across numeric columns"}
        )
    if datetimes and numeric:
        recs.append(
            {
                "type": "line",
                "x": datetimes[0],
                "y": numeric[0],
                "reason": f"{numeric[0]} over {datetimes[0]}",
            }
        )
    return recs[:limit]


def summary(df: pd.DataFrame) -> dict:
    return {
        "numeric": numeric_summary(df),
        "correlations": correlations(df),
        "recommended_charts": recommend_charts(df),
    }
