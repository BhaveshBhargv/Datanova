"""Tests for Phase 9 insights & recommendations."""
import numpy as np
import pandas as pd
import pytest

LIST = "/api/datasets"


def _upload_df(client, headers, df: pd.DataFrame) -> dict:
    buf = df.to_csv(index=False).encode()
    return client.post(
        f"{LIST}/upload", files={"file": ("d.csv", buf, "text/csv")}, headers=headers
    ).json()


def _messy_df() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 60
    x = rng.normal(size=n)
    df = pd.DataFrame(
        {
            "x": x,
            "y": x * 2 + rng.normal(scale=0.1, size=n),  # strong correlation with x
            "mostly_missing": [1.0] + [np.nan] * (n - 1),  # ~98% missing
            "region": ["A"] * 55 + ["B"] * 5,  # dominant category (>80%)
        }
    )
    # Introduce duplicate rows.
    df = pd.concat([df, df.iloc[[0, 1]]], ignore_index=True)
    return df


@pytest.fixture()
def force_fallback(monkeypatch):
    monkeypatch.setattr("app.services.narrate.llm.generate", lambda *a, **k: None)


def test_insights_detects_issues(client, auth_headers):
    headers = auth_headers()
    ds = _upload_df(client, headers, _messy_df())
    r = client.get(f"{LIST}/{ds['id']}/insights", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 3
    categories = {i["category"] for i in body["insights"]}
    titles = " ".join(i["title"].lower() for i in body["insights"])
    assert "data_quality" in categories  # missing / duplicates
    assert "statistical" in categories  # correlation or dominant category
    assert "duplicate" in titles
    assert "missing" in titles
    # Every insight carries a severity and (mostly) a recommendation.
    assert all(i["severity"] in ("critical", "warning", "info") for i in body["insights"])
    # Sorted by severity (critical/warning before info).
    sev_rank = {"critical": 0, "warning": 1, "info": 2}
    ranks = [sev_rank[i["severity"]] for i in body["insights"]]
    assert ranks == sorted(ranks)


def test_insights_counts_match(client, auth_headers):
    headers = auth_headers()
    ds = _upload_df(client, headers, _messy_df())
    body = client.get(f"{LIST}/{ds['id']}/insights", headers=headers).json()
    assert sum(body["counts"].values()) == body["total"]


def test_insights_include_model_when_experiment_exists(client, auth_headers):
    headers = auth_headers()
    rng = np.random.default_rng(1)
    n = 90
    f1 = rng.normal(size=n)
    df = pd.DataFrame({"f1": f1, "f2": rng.normal(size=n), "label": (f1 > 0).astype(int)})
    ds = _upload_df(client, headers, df)
    exp = client.post(
        f"{LIST}/{ds['id']}/experiments", json={"target": "label"}, headers=headers
    ).json()
    assert exp["status"] == "completed"

    body = client.get(f"{LIST}/{ds['id']}/insights", headers=headers).json()
    model_insights = [i for i in body["insights"] if i["category"] == "model"]
    assert len(model_insights) >= 1
    joined = " ".join(i["title"] for i in model_insights).lower()
    assert "best model" in joined or "top predictors" in joined


def test_insights_narrative_fallback(client, auth_headers, force_fallback):
    headers = auth_headers()
    ds = _upload_df(client, headers, _messy_df())
    r = client.post(f"{LIST}/{ds['id']}/insights/narrative", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "fallback"
    assert len(body["text"]) > 0


def test_insights_ownership_enforced(client, auth_headers):
    alice = auth_headers("alice@example.com")
    bob = auth_headers("bob@example.com")
    ds = _upload_df(client, alice, _messy_df())
    assert client.get(f"{LIST}/{ds['id']}/insights", headers=bob).status_code == 404
