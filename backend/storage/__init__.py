from backend.config import Settings
from backend.storage.base import BaseVectorStore


def get_vector_store(settings: Settings) -> BaseVectorStore:
    if settings.vector_store_backend == "chromadb":
        from backend.storage.chroma import ChromaBackend
        return ChromaBackend(settings)
    elif settings.vector_store_backend == "opensearch":
        from backend.storage.opensearch import OpenSearchBackend
        return OpenSearchBackend(settings)
    raise ValueError(f"Unknown VECTOR_STORE_BACKEND: {settings.vector_store_backend}")
