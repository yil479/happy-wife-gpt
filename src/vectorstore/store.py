"""
Stage 4: Vector Store
Persist embedded chunks in ChromaDB so they can be searched by similarity.
ChromaDB runs locally — no external service needed for development.
"""

import os
import chromadb
from chromadb.config import Settings


def _get_client() -> chromadb.ClientAPI:
    persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )


def get_or_create_collection(name: str = "rag_docs") -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
    collection_name: str = "rag_docs",
) -> None:
    collection = get_or_create_collection(collection_name)
    collection.add(
        ids=[f"chunk_{i}" for i in range(len(chunks))],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    print(f"Stored {len(chunks)} chunks in collection '{collection_name}'")


def query_collection(
    query_embedding: list[float],
    n_results: int = 5,
    collection_name: str = "rag_docs",
) -> list[dict]:
    collection = get_or_create_collection(collection_name)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "text": doc,
            "metadata": meta,
            "score": 1 - dist,  # cosine similarity from distance
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]
