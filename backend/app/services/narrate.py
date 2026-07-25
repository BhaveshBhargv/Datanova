"""Turn computed statistics into a plain-English explanation.

Builds a grounded prompt from server-side stats and asks the LLM; if the LLM is
unavailable, returns a deterministic rule-based narrative instead.
"""
from __future__ import annotations

import pandas as pd

from app.services import charts, eda, llm

SYSTEM = (
    "You are a data analyst writing for a business audience. Explain the findings "
    "clearly and concisely in 2-4 short sentences. Use the specific numbers "
    "provided and do not invent facts."
)


def explain(df: pd.DataFrame, kind: str, spec: dict | None) -> tuple[str, str]:
    """Return (text, source) where source is 'llm' or 'fallback'."""
    if kind == "overview":
        facts = _overview_facts(df)
        fallback = _overview_fallback(df)
    elif kind == "chart":
        if not spec:
            raise ValueError("A chart spec is required to explain a chart.")
        data = charts.build(df, spec)
        facts = _chart_facts(data)
        fallback = _chart_fallback(data)
    else:
        raise ValueError(f"Unknown explanation kind '{kind}'.")

    prompt = (
        f"Explain the following {kind} of a dataset to a business user:\n\n{facts}"
    )
    text = llm.generate(prompt, SYSTEM)
    if text:
        return text, "llm"
    return fallback, "fallback"


# --- Fact extraction (fed to the LLM) --------------------------------------


def _overview_facts(df: pd.DataFrame) -> str:
    summary = eda.summary(df)
    lines = [f"Rows: {df.shape[0]}, Columns: {df.shape[1]}."]
    corr = summary["correlations"]
    for pair in _top_correlations(corr, n=3):
        lines.append(
            f"Correlation between {pair[0]} and {pair[1]}: {pair[2]:.2f}."
        )
    for col, stats in list(summary["numeric"].items())[:4]:
        lines.append(
            f"{col}: mean {stats.get('mean')}, min {stats.get('min')}, max {stats.get('max')}."
        )
    return "\n".join(lines)


def _chart_facts(data: dict) -> str:
    lines = [f"Chart: {data['title']} (type: {data['type']})."]
    if data["type"] == "histogram":
        counts = data["series"][0]["data"]
        peak = data["categories"][counts.index(max(counts))] if counts else "n/a"
        lines.append(f"Most values fall in the range {peak}.")
    elif data["type"] in ("bar", "pie"):
        s = data["series"][0]["data"]
        if data["type"] == "bar":
            top = list(zip(data["categories"], s))
        else:
            top = [(d["name"], d["value"]) for d in s]
        top = sorted(top, key=lambda t: t[1], reverse=True)[:3]
        lines.append(
            "Top categories: "
            + ", ".join(f"{name} ({val})" for name, val in top)
            + "."
        )
    elif data["type"] == "correlation_heatmap":
        for pair in _top_heatmap(data, n=3):
            lines.append(f"{pair[0]} and {pair[1]} correlate at {pair[2]:.2f}.")
    elif data["type"] == "scatter":
        lines.append(f"{len(data['series'][0]['data'])} points plotted.")
    elif data["type"] == "box":
        lines.append(f"Box plot across: {', '.join(data['categories'])}.")
    elif data["type"] == "line":
        vals = [v for v in data["series"][0]["data"] if v is not None]
        if vals:
            lines.append(f"Values range from {min(vals)} to {max(vals)}.")
    return "\n".join(lines)


# --- Deterministic fallbacks -----------------------------------------------


def _overview_fallback(df: pd.DataFrame) -> str:
    summary = eda.summary(df)
    parts = [
        f"This dataset has {df.shape[0]} rows and {df.shape[1]} columns."
    ]
    top = _top_correlations(summary["correlations"], n=1)
    if top:
        a, b, v = top[0]
        strength = "strong" if abs(v) >= 0.7 else "moderate" if abs(v) >= 0.4 else "weak"
        direction = "positive" if v > 0 else "negative"
        parts.append(
            f"The strongest relationship is a {strength} {direction} correlation "
            f"between {a} and {b} ({v:.2f})."
        )
    numeric = summary["numeric"]
    if numeric:
        parts.append(f"It contains {len(numeric)} numeric column(s) suitable for analysis.")
    return " ".join(parts)


def _chart_fallback(data: dict) -> str:
    return _chart_facts(data).replace("\n", " ")


# --- Helpers ---------------------------------------------------------------


def _top_correlations(corr: dict, n: int) -> list[tuple[str, str, float]]:
    cols, matrix = corr.get("columns", []), corr.get("matrix", [])
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = matrix[i][j]
            if v is not None:
                pairs.append((cols[i], cols[j], float(v)))
    return sorted(pairs, key=lambda t: abs(t[2]), reverse=True)[:n]


def _top_heatmap(data: dict, n: int) -> list[tuple[str, str, float]]:
    axis = data["extra"]["x"]
    pairs = []
    for i, j, v in data["series"][0]["data"]:
        if i < j and v is not None:
            pairs.append((axis[i], axis[j], float(v)))
    return sorted(pairs, key=lambda t: abs(t[2]), reverse=True)[:n]
