"""Tests for Phase 7 SHAP explainability."""
import numpy as np
import pandas as pd
import pytest

LIST = "/api/datasets"


def _upload_df(client, headers, df: pd.DataFrame) -> dict:
    buf = df.to_csv(index=False).encode()
    return client.post(
        f"{LIST}/upload", files={"file": ("d.csv", buf, "text/csv")}, headers=headers
    ).json()


def _classification_df(n: int = 90) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    f1 = rng.normal(size=n)
    f2 = rng.normal(size=n)
    cat = rng.choice(["x", "y"], size=n)
    label = (f1 + rng.normal(scale=0.3, size=n) > 0).astype(int)
    return pd.DataFrame({"f1": f1, "f2": f2, "cat": cat, "label": label})


def _regression_df(n: int = 90) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    f1 = rng.normal(size=n)
    f2 = rng.normal(size=n)
    y = 3 * f1 + 2 * f2 + rng.normal(scale=0.2, size=n)
    return pd.DataFrame({"f1": f1, "f2": f2, "y": y})


def _make_experiment(client, headers, df, target, **body) -> dict:
    ds = _upload_df(client, headers, df)
    return client.post(
        f"{LIST}/{ds['id']}/experiments",
        json={"target": target, **body},
        headers=headers,
    ).json()


@pytest.fixture()
def force_fallback(monkeypatch):
    monkeypatch.setattr("app.services.narrate.llm.generate", lambda *a, **k: None)


def test_classification_importance(client, auth_headers):
    headers = auth_headers()
    exp = _make_experiment(client, headers, _classification_df(), "label")
    r = client.get(f"/api/experiments/{exp['id']}/importance", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["problem_type"] == "classification"
    features = {f["feature"] for f in body["importance"]}
    assert features <= {"f1", "f2", "cat"}
    assert all(isinstance(f["importance"], (int, float)) for f in body["importance"])
    # Importance is ranked descending.
    imps = [f["importance"] for f in body["importance"]]
    assert imps == sorted(imps, reverse=True)


def test_explain_classification_prediction(client, auth_headers):
    headers = auth_headers()
    exp = _make_experiment(client, headers, _classification_df(), "label")
    r = client.post(
        f"/api/experiments/{exp['id']}/predictions/explain",
        json={"index": 0},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["predicted_label"] in (0, 1)
    assert body["proba"] is not None and len(body["proba"]) == 2
    assert isinstance(body["base_value"], (int, float))
    contribs = {c["feature"] for c in body["contributions"]}
    assert contribs == {"f1", "f2", "cat"}


def test_explain_regression_prediction(client, auth_headers):
    headers = auth_headers()
    exp = _make_experiment(client, headers, _regression_df(), "y", test_size=0.25)
    r = client.post(
        f"/api/experiments/{exp['id']}/predictions/explain",
        json={"index": 3},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body["prediction"], (int, float))
    assert body["proba"] is None
    assert len(body["contributions"]) == 2  # f1, f2


def test_explain_prediction_index_out_of_range(client, auth_headers):
    headers = auth_headers()
    exp = _make_experiment(client, headers, _regression_df(30), "y")
    r = client.post(
        f"/api/experiments/{exp['id']}/predictions/explain",
        json={"index": 9999},
        headers=headers,
    )
    assert r.status_code == 400


def test_narrative_fallback(client, auth_headers, force_fallback):
    headers = auth_headers()
    exp = _make_experiment(client, headers, _classification_df(), "label")
    r = client.post(f"/api/experiments/{exp['id']}/narrative", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "fallback"
    assert len(body["text"]) > 0


def test_importance_requires_completed_experiment(client, auth_headers):
    headers = auth_headers()
    # A single-class target makes training fail -> status "failed".
    df = _classification_df()
    df["label"] = 0
    exp = _make_experiment(client, headers, df, "label")
    assert exp["status"] == "failed"
    r = client.get(f"/api/experiments/{exp['id']}/importance", headers=headers)
    assert r.status_code == 409


def test_explain_ownership_enforced(client, auth_headers):
    alice = auth_headers("alice@example.com")
    bob = auth_headers("bob@example.com")
    exp = _make_experiment(client, alice, _classification_df(), "label")
    assert (
        client.get(f"/api/experiments/{exp['id']}/importance", headers=bob).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/experiments/{exp['id']}/predictions/explain",
            json={"index": 0},
            headers=bob,
        ).status_code
        == 404
    )
