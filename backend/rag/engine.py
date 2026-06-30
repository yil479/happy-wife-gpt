from typing import AsyncGenerator, Literal

from llama_index.core import VectorStoreIndex
from llama_index.core import Settings as LlamaSettings
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.openai import OpenAIEmbedding

from backend.config import Settings
from backend.storage.base import BaseVectorStore
from backend.rag.prompts import MARRIAGE_COUNSELOR_SYSTEM_PROMPT


class RAGEngine:

    def __init__(self, settings: Settings, store: BaseVectorStore):
        self._settings = settings
        self._store = store
        self._session_memories: dict[str, ChatMemoryBuffer] = {}

        # Configure LlamaIndex global settings once at construction time
        LlamaSettings.llm = Anthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
        )
        LlamaSettings.embed_model = OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

        # Build a VectorStoreIndex for each collection
        self._indexes: dict[str, VectorStoreIndex] = {
            col: VectorStoreIndex.from_vector_store(
                vector_store=store.get_store(col)
            )
            for col in ("experiences", "advice")
        }

    def _get_memory(self, session_id: str) -> ChatMemoryBuffer:
        if session_id not in self._session_memories:
            self._session_memories[session_id] = ChatMemoryBuffer.from_defaults(
                token_limit=self._settings.memory_token_limit
            )
        return self._session_memories[session_id]

    def _build_retriever(self, collection: Literal["experiences", "advice", "both"]):
        top_k = self._settings.retrieval_top_k
        if collection != "both":
            return self._indexes[collection].as_retriever(similarity_top_k=top_k)

        # Merge both collections with QueryFusionRetriever
        from llama_index.core.retrievers import QueryFusionRetriever
        return QueryFusionRetriever(
            retrievers=[
                self._indexes["experiences"].as_retriever(similarity_top_k=top_k),
                self._indexes["advice"].as_retriever(similarity_top_k=top_k),
            ],
            num_queries=1,
            use_async=True,
        )

    def _build_chat_engine(
        self,
        session_id: str,
        collection: Literal["experiences", "advice", "both"],
    ) -> CondensePlusContextChatEngine:
        return CondensePlusContextChatEngine.from_defaults(
            retriever=self._build_retriever(collection),
            memory=self._get_memory(session_id),
            system_prompt=MARRIAGE_COUNSELOR_SYSTEM_PROMPT,
            verbose=False,
        )

    def _extract_sources(self, response) -> list[dict]:
        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                sources.append({
                    "text": node.text[:200],
                    "score": round(float(node.score or 0.0), 3),
                    "source": node.metadata.get("filename", "unknown"),
                    "collection": node.metadata.get("collection", "unknown"),
                })
        return sources

    async def chat(
        self,
        session_id: str,
        message: str,
        collection: Literal["experiences", "advice", "both"] = "both",
    ) -> dict:
        engine = self._build_chat_engine(session_id, collection)
        response = await engine.achat(message)
        return {
            "answer": str(response),
            "sources": self._extract_sources(response),
        }

    async def chat_stream(
        self,
        session_id: str,
        message: str,
        collection: Literal["experiences", "advice", "both"] = "both",
    ) -> AsyncGenerator[str, None]:
        engine = self._build_chat_engine(session_id, collection)
        streaming_response = await engine.astream_chat(message)
        async for token in streaming_response.async_response_gen():
            yield token
