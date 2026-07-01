import io
from unittest.mock import MagicMock, patch

from tests.conftest import AUTH_HEADERS


def test_chat_rate_limit_exceeded(client):
    session_id = client.post("/sessions", headers=AUTH_HEADERS).json()["session_id"]

    statuses = []
    for _ in range(21):
        resp = client.post(
            "/chat",
            headers=AUTH_HEADERS,
            json={"session_id": session_id, "message": "hi", "stream": False},
        )
        statuses.append(resp.status_code)

    assert statuses[:20] == [200] * 20
    assert statuses[20] == 429


def test_ingest_rate_limit_exceeded(client, mock_store):
    statuses = []
    with patch("backend.rag.ingestion.VectorStoreIndex") as mock_vi:
        mock_vi.from_vector_store.return_value = MagicMock()
        for _ in range(11):
            resp = client.post(
                "/ingest",
                headers=AUTH_HEADERS,
                params={"collection": "advice"},
                files={"file": ("tips.txt", io.BytesIO(b"Some marriage advice here."), "text/plain")},
            )
            statuses.append(resp.status_code)

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429
