"""Tests for Phase 5 conversational assistant (LLM mocked — no real API calls)."""
import pytest

from app.services.sql_safety import SqlSafetyError, validate_read_only

LIST = "/api/datasets"
SAMPLE = (
    "region,income\n"
    "north,100\n"
    "north,300\n"
    "south,200\n"
    "south,400\n"
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
def conversation(dataset, client):
    headers, dsid = dataset
    conv = client.post(
        f"{LIST}/{dsid}/conversations", json={"title": "Chat"}, headers=headers
    ).json()
    return headers, dsid, conv["id"]


def _mock_llm(monkeypatch, responses):
    it = iter(responses)
    monkeypatch.setattr(
        "app.services.assistant.llm.generate", lambda *a, **k: next(it)
    )
    monkeypatch.setattr("app.services.assistant.llm.enabled", lambda: True)


# --- sql_safety unit tests -------------------------------------------------


def test_sql_safety_allows_select():
    assert validate_read_only("SELECT * FROM data") == "SELECT * FROM data"


@pytest.mark.parametrize(
    "bad",
    [
        "DELETE FROM data",
        "DROP TABLE data",
        "SELECT 1; DROP TABLE data",
        "UPDATE data SET x=1",
        "INSERT INTO data VALUES (1)",
    ],
)
def test_sql_safety_blocks_writes(bad):
    with pytest.raises(SqlSafetyError):
        validate_read_only(bad)


# --- assistant flow --------------------------------------------------------


def test_ask_question_runs_sql_and_explains(conversation, client, monkeypatch):
    headers, _, cid = conversation
    _mock_llm(
        monkeypatch,
        [
            "SELECT region, AVG(income) AS avg_income FROM data GROUP BY region",
            "Income is higher in the south than the north.",
        ],
    )
    r = client.post(
        f"/api/conversations/{cid}/messages",
        json={"content": "What is average income by region?"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    msg = r.json()
    assert msg["role"] == "assistant"
    assert msg["error"] is None
    assert msg["sql"].lower().startswith("select")
    assert msg["result_columns"] == ["region", "avg_income"]
    rows = {row["region"]: row["avg_income"] for row in msg["result_rows"]}
    assert rows == {"north": 200.0, "south": 300.0}
    assert "south" in msg["content"].lower()


def test_unsafe_generated_sql_is_blocked(conversation, client, monkeypatch):
    headers, _, cid = conversation
    _mock_llm(monkeypatch, ["DELETE FROM data"])
    r = client.post(
        f"/api/conversations/{cid}/messages",
        json={"content": "Delete everything"},
        headers=headers,
    )
    assert r.status_code == 200
    msg = r.json()
    assert msg["error"] is not None
    assert msg["result_rows"] is None  # nothing executed


def test_sql_extracted_from_code_fence(conversation, client, monkeypatch):
    headers, _, cid = conversation
    _mock_llm(
        monkeypatch,
        ["```sql\nSELECT COUNT(*) AS n FROM data\n```", "There are four rows."],
    )
    r = client.post(
        f"/api/conversations/{cid}/messages",
        json={"content": "How many rows?"},
        headers=headers,
    )
    msg = r.json()
    assert msg["result_rows"] == [{"n": 4}]


def test_assistant_without_key_is_graceful(conversation, client, monkeypatch):
    headers, _, cid = conversation
    monkeypatch.setattr("app.services.assistant.llm.enabled", lambda: False)
    r = client.post(
        f"/api/conversations/{cid}/messages",
        json={"content": "anything"},
        headers=headers,
    )
    assert r.status_code == 200
    msg = r.json()
    assert msg["error"] == "llm_disabled"
    assert "api key" in msg["content"].lower()
    assert msg["result_rows"] is None


def test_conversation_history_persists(conversation, client, monkeypatch):
    headers, dsid, cid = conversation
    _mock_llm(monkeypatch, ["SELECT COUNT(*) AS n FROM data", "Four rows."])
    client.post(
        f"/api/conversations/{cid}/messages",
        json={"content": "count?"},
        headers=headers,
    )
    detail = client.get(f"/api/conversations/{cid}", headers=headers).json()
    # user question + assistant answer
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["role"] == "user"
    assert detail["messages"][1]["role"] == "assistant"


def test_list_and_delete_conversation(dataset, client):
    headers, dsid = dataset
    conv = client.post(
        f"{LIST}/{dsid}/conversations", json={"title": "Chat"}, headers=headers
    ).json()
    listing = client.get(f"{LIST}/{dsid}/conversations", headers=headers).json()
    assert len(listing) == 1
    assert (
        client.delete(f"/api/conversations/{conv['id']}", headers=headers).status_code
        == 204
    )
    assert client.get(f"/api/conversations/{conv['id']}", headers=headers).status_code == 404


def test_conversation_ownership_enforced(conversation, client, auth_headers):
    _, _, cid = conversation
    bob = auth_headers("bob@example.com")
    assert client.get(f"/api/conversations/{cid}", headers=bob).status_code == 404
    assert (
        client.post(
            f"/api/conversations/{cid}/messages",
            json={"content": "hi"},
            headers=bob,
        ).status_code
        == 404
    )
