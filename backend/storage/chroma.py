import chromadb
from chromadb.config import Settings as ChromaSettings
from llama_index.vector_stores.chroma import ChromaVectorStore

from backend.config import Settings
from backend.storage.base import BaseVectorStore

COLLECTIONS = ("experiences", "advice")


class ChromaBackend(BaseVectorStore):

    def __init__(self, settings: Settings):
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Pre-create both collections on startup
        for name in COLLECTIONS:
            self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )

    def get_store(self, collection: str) -> ChromaVectorStore:
        chroma_collection = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )
        return ChromaVectorStore(chroma_collection=chroma_collection)

    def list_documents(self, collection: str) -> list[dict]:
        col = self._client.get_collection(collection)
        results = col.get(include=["metadatas"])
        # Deduplicate by doc_id — each document has many chunk nodes
        seen: dict[str, dict] = {}
        for meta in results["metadatas"]:
            doc_id = meta.get("doc_id")
            if doc_id and doc_id not in seen:
                seen[doc_id] = {
                    "doc_id": doc_id,
                    "filename": meta.get("filename", "unknown"),
                    "collection": meta.get("collection", collection),
                    "ingested_at": meta.get("ingested_at", ""),
                    "chunk_count": 0,
                }
        # Count chunks per doc_id
        for meta in results["metadatas"]:
            doc_id = meta.get("doc_id")
            if doc_id and doc_id in seen:
                seen[doc_id]["chunk_count"] += 1
        return list(seen.values())

    def delete_document(self, doc_id: str, collection: str) -> bool:
        col = self._client.get_collection(collection)
        results = col.get(where={"doc_id": {"$eq": doc_id}})
        if not results["ids"]:
            return False
        col.delete(ids=results["ids"])
        return True
