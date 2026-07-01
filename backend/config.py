from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys
    openai_api_key: str = ""
    api_key: str = ""  # X-API-Key header; leave empty to disable auth in local dev

    # Model configuration
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Storage backend
    storage_backend: Literal["local", "s3"] = "local"
    local_data_dir: str = "./data"
    s3_bucket: str = ""

    # Vector store backend
    vector_store_backend: Literal["chromadb", "opensearch"] = "chromadb"
    chroma_persist_dir: str = "./chroma_db"
    opensearch_endpoint: str = ""
    aws_region: str = "ap-southeast-1"

    # Chat history
    chat_history_db_path: str = "./chat_history.db"

    # App
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # RAG tuning
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 5
    min_score: float = 0.3

    # Memory
    memory_token_limit: int = 4096


def get_settings() -> Settings:
    return Settings()
