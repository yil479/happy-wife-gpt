from abc import ABC, abstractmethod


class BaseVectorStore(ABC):
    """
    Abstract vector store interface.
    Concrete implementations: ChromaBackend (local), OpenSearchBackend (AWS).
    """

    @abstractmethod
    def get_store(self, collection: str):
        """Return a LlamaIndex-compatible VectorStore for the given collection."""
        ...

    @abstractmethod
    def list_documents(self, collection: str) -> list[dict]:
        """Return document metadata for all documents in the collection."""
        ...

    @abstractmethod
    def delete_document(self, doc_id: str, collection: str) -> bool:
        """Delete all nodes belonging to doc_id from collection. Returns True if found."""
        ...
