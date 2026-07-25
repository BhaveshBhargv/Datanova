"""Tests for Phase 2 database connections and import (via a temp SQLite DB)."""
import sqlite3

import pytest

from app.core.crypto import decrypt, encrypt

CONN = "/api/connections"


@pytest.fixture()
def sqlite_db(tmp_path):
    """A small SQLite database the connection endpoints can import from."""
    path = tmp_path / "external.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE customers (id INTEGER, name TEXT, spend REAL)")
    con.executemany(
        "INSERT INTO customers VALUES (?, ?, ?)",
        [(1, "Ana", 10.5), (2, "Ben", 20.0), (3, "Cate", 5.25)],
    )
    con.commit()
    con.close()
    return str(path)


def _create_conn(client, headers, sqlite_db, name="local"):
    return client.post(
        CONN,
        json={"name": name, "dialect": "sqlite", "database": sqlite_db},
        headers=headers,
    )


def test_crypto_round_trip():
    token = encrypt("hunter2")
    assert token != b"hunter2"
    assert decrypt(token) == "hunter2"


def test_create_connection_never_returns_secrets(client, auth_headers, sqlite_db):
    r = _create_conn(client, auth_headers(), sqlite_db)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["dialect"] == "sqlite"
    assert "password" not in body
    assert "encrypted_password" not in body


def test_create_connection_bad_target_fails(client, auth_headers):
    r = client.post(
        CONN,
        json={"name": "broken", "dialect": "sqlite", "database": "/no/such/dir/x.db"},
        headers=auth_headers(),
    )
    # SQLite happily opens a new empty file, but a missing directory fails.
    assert r.status_code == 400


def test_postgres_connection_requires_host(client, auth_headers):
    r = client.post(
        CONN,
        json={"name": "pg", "dialect": "postgresql", "database": "app"},
        headers=auth_headers(),
    )
    assert r.status_code == 422  # host required


def test_list_tables(client, auth_headers, sqlite_db):
    headers = auth_headers()
    conn_id = _create_conn(client, headers, sqlite_db).json()["id"]
    r = client.get(f"{CONN}/{conn_id}/tables", headers=headers)
    assert r.status_code == 200
    assert "customers" in r.json()["tables"]


def test_import_table_creates_dataset(client, auth_headers, sqlite_db):
    headers = auth_headers()
    conn_id = _create_conn(client, headers, sqlite_db).json()["id"]
    r = client.post(
        f"{CONN}/{conn_id}/import", json={"table": "customers"}, headers=headers
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_type"] == "database"
    assert body["n_rows"] == 3
    assert body["n_columns"] == 3
    assert body["name"] == "customers"


def test_import_query_creates_dataset(client, auth_headers, sqlite_db):
    headers = auth_headers()
    conn_id = _create_conn(client, headers, sqlite_db).json()["id"]
    r = client.post(
        f"{CONN}/{conn_id}/import",
        json={"query": "SELECT name FROM customers WHERE spend > 8", "name": "big"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "big"
    assert body["n_rows"] == 2
    assert body["n_columns"] == 1


def test_import_rejects_non_select_query(client, auth_headers, sqlite_db):
    headers = auth_headers()
    conn_id = _create_conn(client, headers, sqlite_db).json()["id"]
    r = client.post(
        f"{CONN}/{conn_id}/import",
        json={"query": "DELETE FROM customers"},
        headers=headers,
    )
    assert r.status_code == 400


def test_import_requires_exactly_one_source(client, auth_headers, sqlite_db):
    headers = auth_headers()
    conn_id = _create_conn(client, headers, sqlite_db).json()["id"]
    both = client.post(
        f"{CONN}/{conn_id}/import",
        json={"table": "customers", "query": "SELECT 1"},
        headers=headers,
    )
    neither = client.post(f"{CONN}/{conn_id}/import", json={}, headers=headers)
    assert both.status_code == 422
    assert neither.status_code == 422


def test_connection_ownership_enforced(client, auth_headers, sqlite_db):
    alice = auth_headers("alice@example.com")
    bob = auth_headers("bob@example.com")
    conn_id = _create_conn(client, alice, sqlite_db).json()["id"]

    assert client.get(f"{CONN}/{conn_id}/tables", headers=bob).status_code == 404
    assert client.delete(f"{CONN}/{conn_id}", headers=bob).status_code == 404
    assert client.get(CONN, headers=bob).json() == []
