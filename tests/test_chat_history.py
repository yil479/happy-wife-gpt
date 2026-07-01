import pytest

from tests.conftest import AUTH_HEADERS
from backend.config import Settings
from backend.storage.chat_history import ChatHistoryStore


@pytest.fixture
def store(tmp_path):
    settings = Settings(chat_history_db_path=str(tmp_path / "chat_history.db"))
    return ChatHistoryStore(settings)


def test_load_history_empty_for_unknown_session(store):
    assert store.load_history("nope") == []


def test_save_turn_persists_both_messages_in_order(store):
    store.create_session("s1")
    store.save_turn("s1", "I feel frustrated.", "Take a deep breath.")

    history = store.load_history("s1")
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "I feel frustrated."
    assert history[1]["content"] == "Take a deep breath."


def test_save_turn_appends_across_multiple_turns(store):
    store.create_session("s1")
    store.save_turn("s1", "first", "first reply")
    store.save_turn("s1", "second", "second reply")

    history = store.load_history("s1")
    assert [m["content"] for m in history] == ["first", "first reply", "second", "second reply"]


def test_create_session_persists_row(client):
    resp = client.post("/sessions", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    resp = client.get(f"/sessions/{session_id}/history", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"messages": []}


def test_get_history_no_auth(client):
    resp = client.get("/sessions/some-id/history")
    assert resp.status_code == 401


def test_get_history_returns_persisted_messages(client, history_store):
    session_id = client.post("/sessions", headers=AUTH_HEADERS).json()["session_id"]
    history_store.save_turn(session_id, "hello", "hi there")

    resp = client.get(f"/sessions/{session_id}/history", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert [m["content"] for m in messages] == ["hello", "hi there"]
