"""Tests for Phase 4 EDA, charting, and AI explanations."""
import pytest

LIST = "/api/datasets"

# y = 2x (perfect positive correlation); `cat` is categorical.
SAMPLE = (
    "x,y,cat\n"
    "1,2,a\n"
    "2,4,a\n"
    "3,6,b\n"
    "4,8,b\n"
    "5,10,a\n"
).encode()


@pytest.fixture()
def dataset(client, auth_headers):
    headers = auth_headers()
    ds = client.post(
        LIST + "/upload",
        files={"file": ("d.csv", SAMPLE, "text/csv")},
        headers=headers,
    ).json()
    return headers, ds["id"]


@pytest.fixture()
def force_fallback(monkeypatch):
    """Ensure explanations use the deterministic fallback (no real LLM call)."""
    monkeypatch.setattr("app.services.narrate.llm.generate", lambda *a, **k: None)


def test_eda_summary(dataset, client):
    headers, dsid = dataset
    r = client.get(f"{LIST}/{dsid}/eda/summary", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["correlations"]["columns"]) == {"x", "y"}
    # Perfect correlation between x and y.
    matrix = body["correlations"]["matrix"]
    assert matrix[0][1] == pytest.approx(1.0)
    assert len(body["recommended_charts"]) > 0
    assert "x" in body["numeric"]


def test_chart_histogram(dataset, client):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/chart",
        json={"type": "histogram", "column": "x", "bins": 5},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["type"] == "histogram"
    assert sum(data["series"][0]["data"]) == 5  # every row counted once


def test_chart_bar(dataset, client):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/chart", json={"type": "bar", "column": "cat"}, headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    counts = dict(zip(data["categories"], data["series"][0]["data"]))
    assert counts == {"a": 3, "b": 2}


def test_chart_scatter(dataset, client):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/chart",
        json={"type": "scatter", "x": "x", "y": "y"},
        headers=headers,
    )
    assert r.status_code == 200
    assert len(r.json()["series"][0]["data"]) == 5


def test_chart_correlation_heatmap(dataset, client):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/chart",
        json={"type": "correlation_heatmap"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["extra"]["x"] == ["x", "y"]
    assert len(data["series"][0]["data"]) == 4  # 2x2 matrix


def test_chart_box_and_pie(dataset, client):
    headers, dsid = dataset
    box = client.post(
        f"{LIST}/{dsid}/chart", json={"type": "box", "column": "x"}, headers=headers
    )
    assert box.status_code == 200
    assert box.json()["categories"] == ["x"]

    pie = client.post(
        f"{LIST}/{dsid}/chart", json={"type": "pie", "column": "cat"}, headers=headers
    )
    assert pie.status_code == 200
    assert len(pie.json()["series"][0]["data"]) == 2


def test_chart_unknown_column_rejected(dataset, client):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/chart",
        json={"type": "histogram", "column": "nope"},
        headers=headers,
    )
    assert r.status_code == 400


def test_chart_non_numeric_rejected(dataset, client):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/chart",
        json={"type": "histogram", "column": "cat"},
        headers=headers,
    )
    assert r.status_code == 400


def test_chart_invalid_type_rejected(dataset, client):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/chart", json={"type": "bogus"}, headers=headers
    )
    assert r.status_code == 422  # rejected by the schema


def test_explain_overview_fallback(dataset, client, force_fallback):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/explain", json={"kind": "overview"}, headers=headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "fallback"
    assert len(body["text"]) > 0
    assert "5 rows" in body["text"]


def test_explain_chart_fallback(dataset, client, force_fallback):
    headers, dsid = dataset
    r = client.post(
        f"{LIST}/{dsid}/explain",
        json={"kind": "chart", "spec": {"type": "histogram", "column": "x"}},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["source"] == "fallback"
    assert len(r.json()["text"]) > 0


def test_eda_ownership_enforced(client, auth_headers, dataset):
    _, dsid = dataset
    bob = auth_headers("bob@example.com")
    assert client.get(f"{LIST}/{dsid}/eda/summary", headers=bob).status_code == 404
    assert (
        client.post(
            f"{LIST}/{dsid}/chart",
            json={"type": "histogram", "column": "x"},
            headers=bob,
        ).status_code
        == 404
    )
