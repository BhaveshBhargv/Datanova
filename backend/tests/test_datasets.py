"""Tests for Phase 2 dataset upload and management."""
import io

import pandas as pd

UPLOAD = "/api/datasets/upload"
LIST = "/api/datasets"


def _csv_bytes() -> bytes:
    return b"name,age,active\nAlice,30,true\nBob,,false\n"


def _xlsx_bytes() -> bytes:
    buf = io.BytesIO()
    pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]}).to_excel(buf, index=False)
    return buf.getvalue()


def _upload(client, headers, filename, data, content_type):
    return client.post(
        UPLOAD, files={"file": (filename, data, content_type)}, headers=headers
    )


def test_upload_csv_creates_dataset(client, auth_headers):
    headers = auth_headers()
    r = _upload(client, headers, "people.csv", _csv_bytes(), "text/csv")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "people"
    assert body["source_type"] == "upload"
    assert body["n_rows"] == 2
    assert body["n_columns"] == 3
    names = {c["name"]: c for c in body["columns"]}
    assert set(names) == {"name", "age", "active"}
    # `age` has a missing value -> nullable.
    assert names["age"]["nullable"] is True


def test_upload_xlsx_creates_dataset(client, auth_headers):
    headers = auth_headers()
    r = _upload(
        client,
        headers,
        "sheet.xlsx",
        _xlsx_bytes(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert r.status_code == 201, r.text
    assert r.json()["n_rows"] == 3
    assert r.json()["file_format"] == "xlsx"


def test_upload_rejects_unsupported_extension(client, auth_headers):
    r = _upload(client, auth_headers(), "notes.txt", b"hello", "text/plain")
    assert r.status_code == 400


def test_upload_rejects_empty_file(client, auth_headers):
    r = _upload(client, auth_headers(), "empty.csv", b"", "text/csv")
    assert r.status_code == 400


def test_upload_requires_auth(client):
    r = _upload(client, {}, "people.csv", _csv_bytes(), "text/csv")
    assert r.status_code == 401


def test_list_and_get_dataset(client, auth_headers):
    headers = auth_headers()
    created = _upload(client, headers, "people.csv", _csv_bytes(), "text/csv").json()

    listing = client.get(LIST, headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    detail = client.get(f"{LIST}/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]


def test_preview_returns_rows(client, auth_headers):
    headers = auth_headers()
    created = _upload(client, headers, "people.csv", _csv_bytes(), "text/csv").json()
    r = client.get(f"{LIST}/{created['id']}/preview?rows=10", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["columns"] == ["name", "age", "active"]
    assert len(body["rows"]) == 2
    # Missing value serialized as null.
    assert body["rows"][1]["age"] is None


def test_rename_dataset(client, auth_headers):
    headers = auth_headers()
    created = _upload(client, headers, "people.csv", _csv_bytes(), "text/csv").json()
    r = client.patch(
        f"{LIST}/{created['id']}", json={"name": "renamed"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"


def test_delete_dataset(client, auth_headers):
    headers = auth_headers()
    created = _upload(client, headers, "people.csv", _csv_bytes(), "text/csv").json()
    assert client.delete(f"{LIST}/{created['id']}", headers=headers).status_code == 204
    assert client.get(f"{LIST}/{created['id']}", headers=headers).status_code == 404


def test_ownership_is_enforced(client, auth_headers):
    alice = auth_headers("alice@example.com")
    bob = auth_headers("bob@example.com")
    created = _upload(client, alice, "people.csv", _csv_bytes(), "text/csv").json()

    # Bob cannot see or touch Alice's dataset.
    assert client.get(f"{LIST}/{created['id']}", headers=bob).status_code == 404
    assert client.delete(f"{LIST}/{created['id']}", headers=bob).status_code == 404
    assert client.get(LIST, headers=bob).json() == []
