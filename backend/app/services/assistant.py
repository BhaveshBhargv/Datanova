"""Conversational assistant: NL question -> safe SQL -> result -> explanation.

The dataset is loaded into a throwaway in-memory SQLite table named `data`. The
LLM writes a read-only SELECT (validated before execution), which runs against the
isolated copy; the result is then explained in plain English. No filesystem or
network access, no touching the application database.
"""
from __future__ import annotations

import json
import re
import sqlite3

import pandas as pd
import pandas.api.types as pdt

from app.services import llm
from app.services.sql_safety import SqlSafetyError, validate_read_only

TABLE = "data"
RESULT_ROW_CAP = 1000
_SYSTEM_SQL = (
    "You are a data analyst. You are given a SQLite table named `data`. "
    "Write a single read-only SQL SELECT query (SQLite dialect) that answers the "
    "user's question. Use double quotes for column names with spaces. Respond with "
    "ONLY the SQL query, no prose, no code fences."
)
_SYSTEM_EXPLAIN = (
    "You are a data analyst writing for a business audience. In 2-4 short sentences, "
    "explain what the query result shows. Use the specific numbers and do not invent facts."
)

_NO_LLM_MESSAGE = (
    "The AI assistant needs a language model API key to answer questions. Set "
    "OPENROUTER_API_KEY in the backend environment to enable it."
)


def _schema_text(df: pd.DataFrame) -> str:
    lines = [f"Table `{TABLE}` with {len(df)} rows. Columns:"]
    for col in df.columns:
        lines.append(f'  - "{col}" ({df[col].dtype})')
    sample = json.loads(df.head(3).to_json(orient="records", date_format="iso"))
    lines.append(f"Sample rows: {json.dumps(sample)}")
    return "\n".join(lines)


def _extract_sql(text: str) -> str:
    """Pull SQL out of a possibly fenced/prosey LLM response."""
    fence = re.search(r"```(?:sql)?\s*(.+?)```", text, re.DOTALL | re.IGNORECASE)
    candidate = fence.group(1) if fence else text
    return candidate.strip()


def _run_sql(df: pd.DataFrame, sql: str) -> tuple[list[str], list[dict]]:
    conn = sqlite3.connect(":memory:")
    try:
        df.to_sql(TABLE, conn, index=False)
        wrapped = f"SELECT * FROM ({sql}) AS _q LIMIT {RESULT_ROW_CAP}"
        result = pd.read_sql_query(wrapped, conn)
    finally:
        conn.close()
    columns = [str(c) for c in result.columns]
    rows = json.loads(result.to_json(orient="records", date_format="iso"))
    return columns, rows


def _fallback_explanation(columns: list[str], rows: list[dict]) -> str:
    if not rows:
        return "The query ran successfully but returned no rows."
    return (
        f"The query returned {len(rows)} row(s) with columns "
        f"{', '.join(columns)}."
    )


def _history_text(history: list[tuple[str, str]]) -> str:
    if not history:
        return ""
    recent = history[-6:]
    lines = [f"{role}: {content}" for role, content in recent]
    return "Recent conversation:\n" + "\n".join(lines) + "\n\n"


def answer(
    df: pd.DataFrame,
    question: str,
    history: list[tuple[str, str]] | None = None,
) -> dict:
    """Return a dict of assistant-message fields for the given question."""
    blank = {
        "content": "",
        "sql": None,
        "result_columns": None,
        "result_rows": None,
        "error": None,
    }

    if not llm.enabled():
        return {**blank, "content": _NO_LLM_MESSAGE, "error": "llm_disabled"}

    prompt = (
        f"{_history_text(history or [])}"
        f"{_schema_text(df)}\n\nQuestion: {question}\n\nSQL:"
    )
    raw = llm.generate(prompt, _SYSTEM_SQL)
    if not raw:
        return {
            **blank,
            "content": "I couldn't reach the language model to write a query.",
            "error": "llm_failed",
        }

    sql = _extract_sql(raw)
    try:
        sql = validate_read_only(sql)
    except SqlSafetyError as exc:
        return {
            **blank,
            "content": "I generated a query that wasn't a safe read-only statement, so I stopped.",
            "sql": sql,
            "error": str(exc),
        }

    try:
        columns, rows = _run_sql(df, sql)
    except Exception as exc:  # noqa: BLE001 - surface query errors to the user
        return {
            **blank,
            "content": "The query failed to run against this dataset.",
            "sql": sql,
            "error": str(exc),
        }

    explain_prompt = (
        f"Question: {question}\nSQL: {sql}\n"
        f"Result columns: {columns}\n"
        f"Result rows (up to 20 shown): {json.dumps(rows[:20])}\n\n"
        "Explain the result:"
    )
    explanation = llm.generate(explain_prompt, _SYSTEM_EXPLAIN) or _fallback_explanation(
        columns, rows
    )

    return {
        "content": explanation,
        "sql": sql,
        "result_columns": columns,
        "result_rows": rows,
        "error": None,
    }
