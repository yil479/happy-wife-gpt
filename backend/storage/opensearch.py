from backend.config import Settings
from backend.storage.base import BaseVectorStore


class OpenSearchBackend(BaseVectorStore):
    """
    AWS OpenSearch Serverless backend — stub for future AWS migration.
    Switch by setting VECTOR_STORE_BACKEND=opensearch in .env.
    """

    def __init__(self, settings: Settings):
        self._endpoint = settings.opensearch_endpoint
        self._region = settings.aws_region

    def get_store(self, collection: str):
        raise NotImplementedError(
            "OpenSearch backend not yet implemented. "
            "Set VECTOR_STORE_BACKEND=chromadb for local development."
        )

    def list_documents(self, collection: str) -> list[dict]:
        raise NotImplementedError

    def delete_document(self, doc_id: str, collection: str) -> bool:
        raise NotImplementedError
