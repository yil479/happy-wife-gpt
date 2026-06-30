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
    return engine


@pytest.fixture
def client(mock_store, mock_engine):
    from backend.main import app

    with patch("backend.main.get_vector_store", return_value=mock_store), \
         patch("backend.main.RAGEngine", return_value=mock_engine):
        with TestClient(app) as c:
            app.state.settings.api_key = TEST_API_KEY
            yield c
