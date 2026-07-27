"""Natural-language -> SQL against a live connected database.

Introspects the real schema, asks the LLM for a dialect-aware read-only SELECT,
validates it, runs EXPLAIN, executes it (row-capped, with a statement timeout),
and explains the result. Read-only throughout.
"""
from __future__ import annotations

import json

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.crypto import decrypt
from app.models.db_connection import DBConnection
from app.services import db_import, llm
from app.services.sql_safety import SqlSafetyError, extract_sql, validate_read_only

MAX_TABLES = 40
MAX_COLS_PER_TABLE = 60

_SYSTEM_SQL = (
    "You are a SQL expert. Given a database schema and a question, write a single "
    "read-only SQL SELECT query in the specified dialect that answers it. Prefer "
    "explicit column lists over SELECT *. Respond with ONLY the SQL, no prose or fences."
)
_SYSTEM_EXPLAIN = (
    "You are a data analyst writing for a business audience. In 2-4 short sentences, "
    "explain what the query result shows using the specific numbers. Do not invent facts."
)
_NO_LLM_MESSAGE = (
    "The AI query assistant needs a language model API key. Set OPENROUTER_API_KEY "
    "in the backend environment to enable natural-language queries."
)


def introspect_schema(engine: Engine) -> list[dict]:
    inspector = inspect(engine)
    schema = []
    for table in inspector.get_table_names()[:MAX_TABLES]:
        columns = inspector.get_columns(table)[:MAX_COLS_PER_TABLE]
        schema.append(
            {
                "table": table,
                "columns": [
                    {"name": c["name"], "type": str(c["type"])} for c in columns
                ],
            }
        )
    return schema


def _schema_text(schema: list[dict]) -> str:
    lines = []
    for t in schema:
        cols = ", ".join(f'{c["name"]} {c["type"]}' for c in t["columns"])
        lines.append(f'{t["table"]}({cols})')
    return "\n".join(lines)


def explain_plan(engine: Engine, dialect: str, sql: str) -> list[str]:
    prefix = "EXPLAIN QUERY PLAN " if dialect == "sqlite" else "EXPLAIN "
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(prefix + sql)).fetchall()
        return [" | ".join(str(x) for x in row) for row in rows]
    except Exception:  # noqa: BLE001 - EXPLAIN is best-effort
        return []


def run_query(engine: Engine, dialect: str, sql: str) -> tuple[list[str], list[dict]]:
    cap = int(settings.NL_SQL_ROW_CAP)
    ms = int(settings.NL_SQL_TIMEOUT_MS)
    wrapped = f"SELECT * FROM ({sql}) AS _sub LIMIT {cap}"
    with engine.connect() as conn:
        if dialect == "postgresql":
            conn.exec_driver_sql(f"SET statement_timeout = {ms}")
        elif dialect == "mysql":
            conn.exec_driver_sql(f"SET SESSION max_execution_time = {ms}")
        result = pd.read_sql_query(text(wrapped), conn)
    columns = [str(c) for c in result.columns]
    rows = json.loads(result.to_json(orient="records", date_format="iso"))
    return columns, rows


def optimization_notes(sql: str) -> list[str]:
    low = sql.lower()
    notes = []
    if "select *" in low:
        notes.append("Uses SELECT * — select only the columns you need to reduce I/O.")
    if " where " not in low:
        notes.append("No WHERE clause — this may scan the entire table.")
    if " limit " not in low:
        notes.append("No LIMIT in the generated query — results were capped automatically.")
    if " join " in low and " on " not in low:
        notes.append("A JOIN without an ON clause can produce a cross join.")
    return notes


def _generate_sql(schema_text: str, dialect: str, question: str) -> str | None:
    prompt = (
        f"Dialect: {dialect}\nSchema:\n{schema_text}\n\n"
        f"Question: {question}\n\nSQL:"
    )
    return llm.generate(prompt, _SYSTEM_SQL)


def _explain_results(question, sql, columns, rows) -> str:
    prompt = (
        f"Question: {question}\nSQL: {sql}\nColumns: {columns}\n"
        f"Rows (up to 20): {json.dumps(rows[:20])}\n\nExplain the result:"
    )
    fallback = (
        f"The query returned {len(rows)} row(s) with columns {', '.join(columns)}."
        if rows
        else "The query ran successfully but returned no rows."
    )
    return llm.generate(prompt, _SYSTEM_EXPLAIN) or fallback


def answer(connection: DBConnection, question: str) -> dict:
    """Return a dict of NL->SQL response fields for the question."""
    blank = {
        "sql": None,
        "columns": None,
        "rows": None,
        "row_count": None,
        "plan": [],
        "optimization_notes": [],
        "source": None,
    }

    if not llm.enabled():
        return {**blank, "explanation": _NO_LLM_MESSAGE, "error": "llm_disabled"}

    pw = decrypt(connection.encrypted_password) if connection.encrypted_password else None
    engine = db_import.build_engine(
        dialect=connection.dialect,
        database=connection.database,
        host=connection.host,
        port=connection.port,
        username=connection.username,
        password=pw,
    )

    try:
        schema = introspect_schema(engine)
    except Exception as exc:  # noqa: BLE001
        return {**blank, "explanation": "Could not read the database schema.", "error": str(exc)}

    raw = _generate_sql(_schema_text(schema), connection.dialect, question)
    if not raw:
        return {**blank, "explanation": "I couldn't reach the language model.", "error": "llm_failed"}

    sql = extract_sql(raw)
    try:
        sql = validate_read_only(sql)
    except SqlSafetyError as exc:
        return {
            **blank,
            "sql": sql,
            "explanation": "I generated a query that wasn't a safe read-only statement, so I stopped.",
            "error": str(exc),
        }

    plan = explain_plan(engine, connection.dialect, sql)
    try:
        columns, rows = run_query(engine, connection.dialect, sql)
    except Exception as exc:  # noqa: BLE001 - surface query errors
        return {
            **blank,
            "sql": sql,
            "plan": plan,
            "explanation": "The query failed to run against the database.",
            "error": str(exc),
        }

    return {
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "plan": plan,
        "optimization_notes": optimization_notes(sql),
        "explanation": _explain_results(question, sql, columns, rows),
        "source": "llm",
        "error": None,
    }
