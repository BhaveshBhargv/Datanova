"""Tests for Phase 8 NL->SQL over connected databases (LLM mocked)."""
import sqlite3

import pytest

CONN = "/api/connections"


@pytest.fixture()
def sqlite_db(tmp_path):
    path = tmp_path / "shop.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE customers (id INTEGER, name TEXT, spend REAL)")
    con.executemany(
        "INSERT INTO customers VALUES (?, ?, ?)",
        [(1, "Ana", 100.0), (2, "Ben", 250.0), (3, "Cate", 60.0)],
    )
    con.commit()
    con.close()
    return str(path)


@pytest.fixture()
def connection(client, auth_headers, sqlite_db):
    headers = auth_headers()
    conn = client.post(
        CONN,
        json={"name": "shop", "dialect": "sqlite", "database": sqlite_db},
        headers=headers,
    ).json()
    return headers, conn["id"]


def _mock_llm(monkeypatch, responses):
    it = iter(responses)
    monkeypatch.setattr("app.services.nl_sql.llm.generate", lambda *a, **k: next(it))
    monkeypatch.setattr("app.services.nl_sql.llm.enabled", lambda: True)


def test_get_schema(connection, client):
    headers, cid = connection
    r = client.get(f"{CONN}/{cid}/schema", headers=headers)
    assert r.status_code == 200, r.text
    tables = {t["table"] for t in r.json()["tables"]}
    assert "customers" in tables
    cols = {
        c["name"]
        for t in r.json()["tables"]
        if t["table"] == "customers"
        for c in t["columns"]
    }
    assert {"id", "name", "spend"} <= cols


def test_nl_query_runs_and_explains(connection, client, monkeypatch):
    headers, cid = connection
    _mock_llm(
        monkeypatch,
        [
            "SELECT name, spend FROM customers ORDER BY spend DESC",
            "Ben is the top spender at 250.",
        ],
    )
    r = client.post(
        f"{CONN}/{cid}/query",
        json={"question": "Who spends the most?"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["error"] is None
    assert body["source"] == "llm"
    assert body["columns"] == ["name", "spend"]
    assert body["rows"][0]["name"] == "Ben"
    assert body["row_count"] == 3
    assert len(body["plan"]) > 0  # EXPLAIN QUERY PLAN produced rows
    assert "Ben" in body["explanation"]


def test_query_is_persisted_to_history(connection, client, monkeypatch):
    headers, cid = connection
    _mock_llm(monkeypatch, ["SELECT COUNT(*) AS n FROM customers", "Three customers."])
    client.post(
        f"{CONN}/{cid}/query", json={"question": "How many?"}, headers=headers
    )
    hist = client.get(f"{CONN}/{cid}/queries", headers=headers).json()
    assert len(hist) == 1
    assert hist[0]["question"] == "How many?"
    assert hist[0]["sql"].lower().startswith("select")


def test_optimization_notes_flag_select_star(connection, client, monkeypatch):
    headers, cid = connection
    _mock_llm(monkeypatch, ["SELECT * FROM customers", "All customers."])
    r = client.post(
        f"{CONN}/{cid}/query", json={"question": "everything"}, headers=headers
    )
    notes = " ".join(r.json()["optimization_notes"]).lower()
    assert "select *" in notes


def test_unsafe_generated_sql_blocked(connection, client, monkeypatch):
    headers, cid = connection
    _mock_llm(monkeypatch, ["DELETE FROM customers"])
    r = client.post(
        f"{CONN}/{cid}/query", json={"question": "wipe it"}, headers=headers
    )
    body = r.json()
    assert body["error"] is not None
    assert body["rows"] is None  # nothing executed


def test_no_key_is_graceful(connection, client, monkeypatch):
    headers, cid = connection
    monkeypatch.setattr("app.services.nl_sql.llm.enabled", lambda: False)
    r = client.post(
        f"{CONN}/{cid}/query", json={"question": "hi"}, headers=headers
    )
    body = r.json()
    assert body["error"] == "llm_disabled"
    assert "api key" in body["explanation"].lower()
    assert body["rows"] is None


def test_nl_query_ownership_enforced(connection, client, auth_headers):
    _, cid = connection
    bob = auth_headers("bob@example.com")
    assert client.get(f"{CONN}/{cid}/schema", headers=bob).status_code == 404
    assert (
        client.post(
            f"{CONN}/{cid}/query", json={"question": "hi"}, headers=bob
        ).status_code
        == 404
    )
