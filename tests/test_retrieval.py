"""
Basic tests for the ingestion and chunking pipeline.
Run with: pytest tests/
"""

from src.ingestion.chunker import chunk_documents


def test_chunk_splits_long_text():
    docs = [{"text": "word " * 300, "metadata": {"source": "test.txt"}}]
    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"]) <= 200  # generous upper bound
        assert "chunk_index" in chunk["metadata"]


def test_chunk_preserves_metadata():
    docs = [{"text": "Hello world.", "metadata": {"source": "test.txt", "page": 1}}]
    chunks = chunk_documents(docs, chunk_size=512, chunk_overlap=0)
    assert chunks[0]["metadata"]["source"] == "test.txt"
    assert chunks[0]["metadata"]["page"] == 1


def test_empty_docs():
    chunks = chunk_documents([], chunk_size=512, chunk_overlap=0)
    assert chunks == []
