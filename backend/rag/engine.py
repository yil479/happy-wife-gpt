from typing import AsyncGenerator, Literal

from llama_index.core import VectorStoreIndex
from llama_index.core import Settings as LlamaSettings
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

from backend.config import Settings
from backend.storage.base import BaseVectorStore
from backend.rag.prompts import MARRIAGE_COUNSELOR_SYSTEM_PROMPT

_EMPTY = "Empty Response"


class RAGEngine:

    def __init__(self, settings: Settings, store: BaseVectorStore):
        self._settings = settings
        self._store = store
        self._session_memories: dict[str, ChatMemoryBuffer] = {}

        LlamaSettings.llm = OpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
        )
        LlamaSettings.embed_model = OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

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

    def _build_direct_messages(self, session_id: str, message: str) -> list[ChatMessage]:
        """Build a message list for direct LLM calls (no RAG context)."""
        memory = self._get_memory(session_id)
        history = memory.get()
        return (
            [ChatMessage(role=MessageRole.SYSTEM, content=MARRIAGE_COUNSELOR_SYSTEM_PROMPT)]
            + history
            + [ChatMessage(role=MessageRole.USER, content=message)]
        )

    def _update_memory(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        memory = self._get_memory(session_id)
        memory.put(ChatMessage(role=MessageRole.USER, content=user_msg))
        memory.put(ChatMessage(role=MessageRole.ASSISTANT, content=assistant_msg))

    async def chat(
        self,
        session_id: str,
        message: str,
        collection: Literal["experiences", "advice", "both"] = "both",
    ) -> dict:
        engine = self._build_chat_engine(session_id, collection)
        response = await engine.achat(message)
        answer = str(response)

        # LlamaIndex returns "Empty Response" when the vector store has no documents.
        # Fall back to a direct LLM call so the counselor still responds.
        if answer.strip() == _EMPTY:
            messages = self._build_direct_messages(session_id, message)
            direct = await LlamaSettings.llm.achat(messages)
            answer = direct.message.content or ""
            self._update_memory(session_id, message, answer)
            return {"answer": answer, "sources": []}

        return {"answer": answer, "sources": self._extract_sources(response)}

    async def chat_stream(
        self,
        session_id: str,
        message: str,
        collection: Literal["experiences", "advice", "both"] = "both",
    ) -> AsyncGenerator[str, None]:
        # Retrieve nodes first to decide which path to take.
        # This avoids yielding LlamaIndex's "Empty Response" sentinel mid-stream.
        retriever = self._build_retriever(collection)
        nodes = await retriever.aretrieve(message)

        if not nodes:
            # No documents — stream directly from the LLM using session memory.
            messages = self._build_direct_messages(session_id, message)
            stream = await LlamaSettings.llm.astream_chat(messages)
            full_text = ""
            async for chunk in stream:
                if chunk.delta:
                    full_text += chunk.delta
                    yield chunk.delta
            self._update_memory(session_id, message, full_text)
        else:
            engine = self._build_chat_engine(session_id, collection)
            streaming_response = await engine.astream_chat(message)
            async for token in streaming_response.async_response_gen():
                yield token
