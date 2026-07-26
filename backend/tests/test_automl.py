"""Tests for Phase 6 AutoML."""
import numpy as np
import pandas as pd
import pytest

from app.services.automl import detect_problem_type

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


def test_detect_problem_type():
    assert detect_problem_type(pd.Series([0, 1, 0, 1, 1])) == "classification"
    assert detect_problem_type(pd.Series(np.arange(100) * 1.5)) == "regression"
    assert detect_problem_type(pd.Series(["a", "b", "a", "c"])) == "classification"


def test_classification_experiment(client, auth_headers):
    headers = auth_headers()
    ds = _upload_df(client, headers, _classification_df())
    r = client.post(
        f"{LIST}/{ds['id']}/experiments", json={"target": "label"}, headers=headers
    )
    assert r.status_code == 201, r.text
    exp = r.json()
    assert exp["problem_type"] == "classification"
    assert exp["status"] == "completed"
    models = {m["model"] for m in exp["results"]}
    assert {"Logistic Regression", "Decision Tree", "Random Forest", "XGBoost"} <= models
    assert exp["best_model_name"] is not None
    # Metrics present and the signal is learnable.
    best = next(m for m in exp["results"] if m["model"] == exp["best_model_name"])
    assert "f1" in best["metrics"]
    assert best["metrics"]["accuracy"] >= 0.7


def test_regression_experiment(client, auth_headers):
    headers = auth_headers()
    ds = _upload_df(client, headers, _regression_df())
    r = client.post(
        f"{LIST}/{ds['id']}/experiments",
        json={"target": "y", "test_size": 0.25},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    exp = r.json()
    assert exp["problem_type"] == "regression"
    assert exp["status"] == "completed"
    best = next(m for m in exp["results"] if m["model"] == exp["best_model_name"])
    assert "r2" in best["metrics"] and "rmse" in best["metrics"]
    assert best["metrics"]["r2"] >= 0.8  # strong linear signal


def test_feature_selection_respected(client, auth_headers):
    headers = auth_headers()
    ds = _upload_df(client, headers, _classification_df())
    r = client.post(
        f"{LIST}/{ds['id']}/experiments",
        json={"target": "label", "features": ["f1", "f2"]},
        headers=headers,
    )
    assert r.status_code == 201
    assert set(r.json()["feature_columns"]) == {"f1", "f2"}


def test_invalid_target_rejected(client, auth_headers):
    headers = auth_headers()
    ds = _upload_df(client, headers, _classification_df())
    r = client.post(
        f"{LIST}/{ds['id']}/experiments", json={"target": "nope"}, headers=headers
    )
    assert r.status_code == 400


def test_list_get_delete_experiment(client, auth_headers):
    headers = auth_headers()
    ds = _upload_df(client, headers, _classification_df())
    exp = client.post(
        f"{LIST}/{ds['id']}/experiments", json={"target": "label"}, headers=headers
    ).json()

    listing = client.get(f"{LIST}/{ds['id']}/experiments", headers=headers)
    assert len(listing.json()) == 1

    got = client.get(f"/api/experiments/{exp['id']}", headers=headers)
    assert got.status_code == 200
    assert got.json()["best_model_name"] == exp["best_model_name"]

    assert (
        client.delete(f"/api/experiments/{exp['id']}", headers=headers).status_code
        == 204
    )
    assert client.get(f"/api/experiments/{exp['id']}", headers=headers).status_code == 404


def test_experiment_ownership_enforced(client, auth_headers):
    alice = auth_headers("alice@example.com")
    bob = auth_headers("bob@example.com")
    ds = _upload_df(client, alice, _classification_df())
    exp = client.post(
        f"{LIST}/{ds['id']}/experiments", json={"target": "label"}, headers=alice
    ).json()

    assert (
        client.post(
            f"{LIST}/{ds['id']}/experiments", json={"target": "label"}, headers=bob
        ).status_code
        == 404
    )
    assert client.get(f"/api/experiments/{exp['id']}", headers=bob).status_code == 404
