"""Tests for Phase 11 workspace summary."""
import numpy as np
import pandas as pd

LIST = "/api/datasets"
SUMMARY = "/api/workspace/summary"


def _upload_df(client, headers, df, name="d.csv") -> dict:
    buf = df.to_csv(index=False).encode()
    return client.post(
        LIST + "/upload", files={"file": (name, buf, "text/csv")}, headers=headers
    ).json()


def _df(n=80):
    rng = np.random.default_rng(0)
    f1 = rng.normal(size=n)
    return pd.DataFrame({"f1": f1, "f2": rng.normal(size=n), "label": (f1 > 0).astype(int)})


def test_empty_workspace(client, auth_headers):
    headers = auth_headers()
    r = client.get(SUMMARY, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["counts"] == {"datasets": 0, "connections": 0, "models": 0, "chats": 0}
    assert body["recent_datasets"] == []


def test_workspace_counts_and_recents(client, auth_headers):
    headers = auth_headers()
    ds = _upload_df(client, headers, _df())
    client.post(
        f"{LIST}/{ds['id']}/experiments", json={"target": "label"}, headers=headers
    )

    body = client.get(SUMMARY, headers=headers).json()
    assert body["counts"]["datasets"] == 1
    assert body["counts"]["models"] == 1
    assert len(body["recent_datasets"]) == 1
    assert len(body["recent_models"]) == 1
    assert body["recent_models"][0]["dataset_name"] == ds["name"]
    assert body["recent_models"][0]["target"] == "label"


def test_workspace_is_owner_scoped(client, auth_headers):
    alice = auth_headers("alice@example.com")
    _upload_df(client, alice, _df())

    bob = auth_headers("bob@example.com")
    body = client.get(SUMMARY, headers=bob).json()
    assert body["counts"]["datasets"] == 0
    assert body["recent_datasets"] == []
