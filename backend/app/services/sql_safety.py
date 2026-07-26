"""Shared read-only SQL validation.

Used both by database imports (Phase 2) and the conversational assistant (Phase 5)
to ensure only a single read-only statement is ever executed.
"""
from __future__ import annotations

import re

_FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "grant", "revoke", "attach", "pragma", "exec", "execute", "merge",
    "replace", "call", "into", "vacuum", "reindex",
}


class SqlSafetyError(Exception):
    """Raised when a query is not a single read-only statement."""


def validate_read_only(query: str) -> str:
    """Return the trimmed query if it is a single read-only statement, else raise."""
    q = query.strip().rstrip(";").strip()
    low = q.lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise SqlSafetyError("Only SELECT queries are allowed.")
    if ";" in q:
        raise SqlSafetyError("Only a single statement is allowed.")
    tokens = set(re.findall(r"[a-z_]+", low))
    forbidden = tokens & _FORBIDDEN_KEYWORDS
    if forbidden:
        raise SqlSafetyError(
            f"Query contains a forbidden keyword: {', '.join(sorted(forbidden))}."
        )
    return q
