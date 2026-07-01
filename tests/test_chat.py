from tests.conftest import AUTH_HEADERS


def test_create_session(client):
    resp = client.post("/sessions", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert len(data["session_id"]) == 36  # UUID4 string


def test_create_session_no_auth(client):
    resp = client.post("/sessions")
    assert resp.status_code == 401


def test_create_session_wrong_key(client):
    resp = client.post("/sessions", headers={"X-API-Key": "bad-key"})
    assert resp.status_code == 401


def test_chat_non_streaming(client):
    session_id = client.post("/sessions", headers=AUTH_HEADERS).json()["session_id"]

    resp = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"session_id": session_id, "message": "I feel frustrated.", "stream": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["answer"] == "Take a deep breath."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["score"] == 0.9


def test_chat_no_auth(client):
    resp = client.post(
        "/chat",
        json={"session_id": "00000000-0000-0000-0000-000000000000", "message": "hi", "stream": False},
    )
    assert resp.status_code == 401


def test_chat_wrong_key(client):
    resp = client.post(
        "/chat",
        headers={"X-API-Key": "wrong"},
        json={"session_id": "00000000-0000-0000-0000-000000000000", "message": "hi", "stream": False},
    )
    assert resp.status_code == 401


def test_chat_rejects_empty_message(client):
    session_id = client.post("/sessions", headers=AUTH_HEADERS).json()["session_id"]
    resp = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"session_id": session_id, "message": "", "stream": False},
    )
    assert resp.status_code == 422


def test_chat_rejects_message_over_max_length(client):
    session_id = client.post("/sessions", headers=AUTH_HEADERS).json()["session_id"]
    resp = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"session_id": session_id, "message": "x" * 4001, "stream": False},
    )
    assert resp.status_code == 422


def test_chat_accepts_message_at_max_length(client):
    session_id = client.post("/sessions", headers=AUTH_HEADERS).json()["session_id"]
    resp = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"session_id": session_id, "message": "x" * 4000, "stream": False},
    )
    assert resp.status_code == 200


def test_health_is_public(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
