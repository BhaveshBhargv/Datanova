"""Tests for Phase 3 profiling and cleaning transformations."""
import io

LIST = "/api/datasets"


def _csv(rows: str) -> bytes:
    return rows.encode()


def _upload(client, headers, data: bytes, filename: str = "d.csv"):
    return client.post(
        LIST + "/upload",
        files={"file": (filename, data, "text/csv")},
        headers=headers,
    )


# A dataset with a missing value, a duplicate row, an outlier, and a
# string column that is really numeric.
SAMPLE = _csv(
    "id,score,city\n"
    "1,10,london\n"
    "2,12,paris\n"
    "3,,london\n"       # missing score
    "4,11,paris\n"
    "5,1000,london\n"   # outlier score
    "4,11,paris\n"      # duplicate of row 4
)


def _make_dataset(client, headers, data=SAMPLE):
    return _upload(client, headers, data).json()


def test_profile_reports_quality(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    r = client.get(f"{LIST}/{ds['id']}/profile", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["n_rows"] == 6
    assert body["duplicate_rows"] == 1
    assert body["missing_cells"] == 1

    cols = {c["name"]: c for c in body["columns"]}
    assert cols["score"]["missing"] == 1
    assert cols["score"]["outliers"] >= 1  # 1000 is an IQR outlier
    assert 0 <= body["quality_score"] <= 100


def test_profile_suggests_type_for_numeric_string(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers, _csv("code\n1\n2\n3\n4\n5\n"))
    # Store the column as text; profiling should then suggest casting it to integer.
    client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "cast_type", "params": {"column": "code", "to": "string"}},
        headers=headers,
    )
    r = client.get(f"{LIST}/{ds['id']}/profile", headers=headers)
    code = {c["name"]: c for c in r.json()["columns"]}["code"]
    assert code["suggested_type"] == "integer"


def test_drop_duplicates(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    r = client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "drop_duplicates", "params": {}},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["n_rows"] == 5  # one duplicate removed


def test_drop_missing_rows(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    r = client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "drop_missing_rows", "params": {"how": "any"}},
        headers=headers,
    )
    assert r.json()["n_rows"] == 5  # the row with missing score removed


def test_impute_missing_median(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    r = client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "impute_missing", "params": {"column": "score", "strategy": "median"}},
        headers=headers,
    )
    assert r.status_code == 200
    profile = client.get(f"{LIST}/{ds['id']}/profile", headers=headers).json()
    score = {c["name"]: c for c in profile["columns"]}["score"]
    assert score["missing"] == 0


def test_handle_outliers_clip(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    r = client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "handle_outliers", "params": {"column": "score", "method": "clip"}},
        headers=headers,
    )
    assert r.status_code == 200
    profile = client.get(f"{LIST}/{ds['id']}/profile", headers=headers).json()
    score = {c["name"]: c for c in profile["columns"]}["score"]
    assert score["max"] < 1000  # outlier clipped down


def test_drop_columns(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    r = client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "drop_columns", "params": {"columns": ["city"]}},
        headers=headers,
    )
    assert r.json()["n_columns"] == 2
    names = {c["name"] for c in r.json()["columns"]}
    assert "city" not in names


def test_cast_type(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers, _csv("code\n1\n2\n3\n"))
    r = client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "cast_type", "params": {"column": "code", "to": "integer"}},
        headers=headers,
    )
    assert r.status_code == 200
    col = {c["name"]: c for c in r.json()["columns"]}["code"]
    assert col["dtype"] == "integer"


def test_invalid_operation_rejected(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    r = client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "delete_everything", "params": {}},
        headers=headers,
    )
    assert r.status_code == 422


def test_transform_on_unknown_column_rejected(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    r = client.post(
        f"{LIST}/{ds['id']}/transformations",
        json={"operation": "drop_columns", "params": {"columns": ["nope"]}},
        headers=headers,
    )
    assert r.status_code == 400


def test_history_undo_and_reset(client, auth_headers):
    headers = auth_headers()
    ds = _make_dataset(client, headers)
    dsid = ds["id"]

    client.post(
        f"{LIST}/{dsid}/transformations",
        json={"operation": "drop_duplicates", "params": {}},
        headers=headers,
    )
    client.post(
        f"{LIST}/{dsid}/transformations",
        json={"operation": "drop_missing_rows", "params": {}},
        headers=headers,
    )
    hist = client.get(f"{LIST}/{dsid}/transformations", headers=headers).json()
    assert [s["operation"] for s in hist] == ["drop_duplicates", "drop_missing_rows"]
    assert [s["order_index"] for s in hist] == [0, 1]

    # After both steps: 6 -> 5 (dupes) -> 4 (missing).
    assert client.get(f"{LIST}/{dsid}", headers=headers).json()["n_rows"] == 4

    # Undo the last step -> back to 5 rows, one step left.
    undone = client.post(f"{LIST}/{dsid}/transformations/undo", headers=headers)
    assert undone.json()["n_rows"] == 5
    assert len(client.get(f"{LIST}/{dsid}/transformations", headers=headers).json()) == 1

    # Reset -> original 6 rows, no steps.
    reset = client.post(f"{LIST}/{dsid}/transformations/reset", headers=headers)
    assert reset.json()["n_rows"] == 6
    assert client.get(f"{LIST}/{dsid}/transformations", headers=headers).json() == []


def test_profiling_ownership_enforced(client, auth_headers):
    alice = auth_headers("alice@example.com")
    bob = auth_headers("bob@example.com")
    ds = _make_dataset(client, alice)
    assert client.get(f"{LIST}/{ds['id']}/profile", headers=bob).status_code == 404
    assert (
        client.post(
            f"{LIST}/{ds['id']}/transformations",
            json={"operation": "drop_duplicates", "params": {}},
            headers=bob,
        ).status_code
        == 404
    )
