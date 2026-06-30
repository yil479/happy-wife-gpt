import io
from unittest.mock import MagicMock, patch

from tests.conftest import AUTH_HEADERS


def test_ingest_txt(client, mock_store):
    mock_index = MagicMock()
    with patch("backend.rag.ingestion.VectorStoreIndex") as mock_vi:
        mock_vi.from_vector_store.return_value = mock_index

        resp = client.post(
            "/ingest",
            headers=AUTH_HEADERS,
            params={"collection": "advice"},
            files={"file": ("tips.txt", io.BytesIO(b"Some marriage advice here."), "text/plain")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["filename"] == "tips.txt"
    assert data["collection"] == "advice"
    assert data["chunks_stored"] >= 1


def test_ingest_md(client, mock_store):
    mock_index = MagicMock()
    with patch("backend.rag.ingestion.VectorStoreIndex") as mock_vi:
        mock_vi.from_vector_store.return_value = mock_index

        resp = client.post(
            "/ingest",
            headers=AUTH_HEADERS,
            params={"collection": "experiences"},
            files={"file": ("fight.md", io.BytesIO(b"# Argument\nWe disagreed about dishes."), "text/markdown")},
        )

    assert resp.status_code == 200
    assert resp.json()["collection"] == "experiences"


def test_ingest_unsupported_ext(client):
    resp = client.post(
        "/ingest",
        headers=AUTH_HEADERS,
        params={"collection": "advice"},
        files={"file": ("report.docx", io.BytesIO(b"binary content"), "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert ".docx" in resp.json()["detail"]


def test_ingest_no_auth(client):
    resp = client.post(
        "/ingest",
        params={"collection": "advice"},
        files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
    )
    assert resp.status_code == 401


def test_list_documents_both(client, mock_store):
    mock_store.list_documents.return_value = [
        {
            "doc_id": "doc_abc123",
            "filename": "advice.txt",
            "collection": "advice",
            "ingested_at": "2026-01-01T00:00:00+00:00",
            "chunk_count": 3,
        }
    ]
    resp = client.get("/documents", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert len(docs) >= 1
    assert docs[0]["doc_id"] == "doc_abc123"


def test_list_documents_by_collection(client, mock_store):
    mock_store.list_documents.return_value = []
    resp = client.get("/documents", headers=AUTH_HEADERS, params={"collection": "experiences"})
    assert resp.status_code == 200
    assert resp.json()["documents"] == []


def test_list_documents_no_auth(client):
    resp = client.get("/documents")
    assert resp.status_code == 401


def test_delete_document(client, mock_store):
    mock_store.delete_document.return_value = True
    resp = client.delete(
        "/documents/doc_abc123",
        headers=AUTH_HEADERS,
        params={"collection": "advice"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "deleted"
    assert body["doc_id"] == "doc_abc123"


def test_delete_document_not_found(client, mock_store):
    mock_store.delete_document.return_value = False
    resp = client.delete(
        "/documents/nonexistent",
        headers=AUTH_HEADERS,
        params={"collection": "advice"},
    )
    assert resp.status_code == 404
