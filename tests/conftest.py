import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

TEST_API_KEY = "test-key-abc"
AUTH_HEADERS = {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.list_documents.return_value = [
        {
            "doc_id": "doc_abc123",
            "filename": "advice.txt",
            "collection": "advice",
            "ingested_at": "2026-01-01T00:00:00+00:00",
            "chunk_count": 3,
        }
    ]
    store.delete_document.return_value = True
    store.get_store.return_value = MagicMock()
    return store


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.chat = AsyncMock(return_value={
        "answer": "Take a deep breath.",
        "sources": [
            {"text": "some advice", "score": 0.9, "source": "book.pdf", "collection": "advice"}
        ],
    })

    async def _chat_stream(session_id, message, collection, sources_out=None):
        for token in ["Take ", "a ", "deep ", "breath."]:
            yield token
        if sources_out is not None:
            sources_out.append(
                {"text": "some advice", "score": 0.9, "source": "book.pdf", "collection": "advice"}
            )

    engine.chat_stream = _chat_stream
    return engine


@pytest.fixture
def history_store(tmp_path):
    from backend.config import Settings
    from backend.storage.chat_history import ChatHistoryStore

    settings = Settings(chat_history_db_path=str(tmp_path / "chat_history.db"))
    return ChatHistoryStore(settings)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from backend.rate_limit import limiter

    limiter.reset()
    yield


@pytest.fixture
def client(mock_store, mock_engine, history_store):
    from backend.main import app

    with patch("backend.main.get_vector_store", return_value=mock_store), \
         patch("backend.main.ChatHistoryStore", return_value=history_store), \
         patch("backend.main.RAGEngine", return_value=mock_engine):
        with TestClient(app) as c:
            app.state.settings.api_key = TEST_API_KEY
            yield c
