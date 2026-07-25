"""Connect to external SQL databases: test, list tables, and import data.

Imports are read-only and row-capped. Table imports reflect the table and use a
parameterized SELECT; raw queries are restricted to a single read-only statement.
"""
from __future__ import annotations

import re

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, inspect, select
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

_DRIVERS = {
    "postgresql": "postgresql+psycopg2",
    "mysql": "mysql+pymysql",
}

_FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "grant", "revoke", "attach", "pragma", "exec", "execute", "merge",
    "replace", "call", "into",
}


class DBImportError(Exception):
    """Raised for connection/import failures (-> HTTP 400)."""


def build_engine(
    dialect: str,
    database: str,
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
    password: str | None = None,
) -> Engine:
    if dialect == "sqlite":
        url = URL.create("sqlite", database=database)
    elif dialect in _DRIVERS:
        url = URL.create(
            _DRIVERS[dialect],
            username=username,
            password=password,
            host=host,
            port=port,
            database=database,
        )
    else:
        raise DBImportError(f"Unsupported dialect '{dialect}'.")
    return create_engine(url, pool_pre_ping=True)


def test_connection(engine: Engine) -> None:
    """Open and close a connection; raise DBImportError on failure."""
    try:
        with engine.connect():
            pass
    except SQLAlchemyError as exc:
        raise DBImportError(f"Connection failed: {exc.__class__.__name__}") from exc


def list_tables(engine: Engine) -> list[str]:
    try:
        return sorted(inspect(engine).get_table_names())
    except SQLAlchemyError as exc:
        raise DBImportError(f"Could not list tables: {exc.__class__.__name__}") from exc


def _validate_read_only(query: str) -> str:
    q = query.strip().rstrip(";").strip()
    low = q.lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise DBImportError("Only SELECT queries are allowed.")
    if ";" in q:
        raise DBImportError("Only a single statement is allowed.")
    tokens = set(re.findall(r"[a-z_]+", low))
    if tokens & _FORBIDDEN_KEYWORDS:
        raise DBImportError("Query contains a forbidden keyword.")
    return q


def import_table(engine: Engine, table: str) -> pd.DataFrame:
    cap = settings.IMPORT_ROW_CAP
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        raise DBImportError(f"Table '{table}' was not found.")
    try:
        meta = MetaData()
        tbl = Table(table, meta, autoload_with=engine)
        stmt = select(tbl).limit(cap)
        return pd.read_sql(stmt, engine)
    except SQLAlchemyError as exc:
        raise DBImportError(f"Import failed: {exc.__class__.__name__}") from exc


def import_query(engine: Engine, query: str) -> pd.DataFrame:
    cap = int(settings.IMPORT_ROW_CAP)
    inner = _validate_read_only(query)
    # cap is an int we control; safe to inline (bound params in LIMIT are not
    # portable across dialects).
    wrapped = f"SELECT * FROM ({inner}) AS _sub LIMIT {cap}"
    try:
        return pd.read_sql(wrapped, engine)
    except SQLAlchemyError as exc:
        raise DBImportError(f"Query failed: {exc.__class__.__name__}") from exc
