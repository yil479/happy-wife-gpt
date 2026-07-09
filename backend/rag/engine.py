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
from backend.storage.chat_history import ChatHistoryStore
from backend.rag.prompts import MARRIAGE_COUNSELOR_SYSTEM_PROMPT, SAFETY_SYSTEM_PROMPT
from backend.rag.safety import (
    SAFETY_RESOURCES_RESPONSE,
    classify_abuse_risk,
    contains_high_risk_language,
)

_EMPTY = "Empty Response"

_ROLE_MAP = {"user": MessageRole.USER, "assistant": MessageRole.ASSISTANT}


class RAGEngine:

    def __init__(self, settings: Settings, store: BaseVectorStore, history: ChatHistoryStore):
        self._settings = settings
        self._store = store
        self._history = history
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
            persisted = self._history.load_history(session_id)
            chat_history = [
                ChatMessage(role=_ROLE_MAP.get(row["role"], MessageRole.USER), content=row["content"])
                for row in persisted
            ]
            self._session_memories[session_id] = ChatMemoryBuffer.from_defaults(
                chat_history=chat_history,
                token_limit=self._settings.memory_token_limit,
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

    def _build_messages_with_system(
        self, session_id: str, message: str, system_prompt: str
    ) -> list[ChatMessage]:
        """Build a message list for direct LLM calls (no RAG context)."""
        memory = self._get_memory(session_id)
        history = memory.get()
        return (
            [ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)]
            + history
            + [ChatMessage(role=MessageRole.USER, content=message)]
        )

    def _build_direct_messages(self, session_id: str, message: str) -> list[ChatMessage]:
        return self._build_messages_with_system(session_id, message, MARRIAGE_COUNSELOR_SYSTEM_PROMPT)

    def _build_safety_messages(self, session_id: str, message: str) -> list[ChatMessage]:
        return self._build_messages_with_system(session_id, message, SAFETY_SYSTEM_PROMPT)

    def _update_memory(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        memory = self._get_memory(session_id)
        memory.put(ChatMessage(role=MessageRole.USER, content=user_msg))
        memory.put(ChatMessage(role=MessageRole.ASSISTANT, content=assistant_msg))

    async def _check_safety(self, session_id: str, message: str) -> tuple[bool, bool]:
        """Returns (is_flagged, is_new_flag). Sticky per session: once flagged, always flagged."""
        if self._history.is_session_flagged(session_id):
            return True, False

        if contains_high_risk_language(message):
            self._history.flag_session_safety(session_id)
            return True, True

        memory = self._get_memory(session_id)
        recent_history = memory.get()[-6:]
        if await classify_abuse_risk(LlamaSettings.llm, message, recent_history):
            self._history.flag_session_safety(session_id)
            return True, True

        return False, False

    async def chat(
        self,
        session_id: str,
        message: str,
        collection: Literal["experiences", "advice", "both"] = "both",
    ) -> dict:
        flagged, is_new_flag = await self._check_safety(session_id, message)
        if flagged:
            if is_new_flag:
                answer = SAFETY_RESOURCES_RESPONSE
            else:
                messages = self._build_safety_messages(session_id, message)
                direct = await LlamaSettings.llm.achat(messages)
                answer = direct.message.content or SAFETY_RESOURCES_RESPONSE
            self._update_memory(session_id, message, answer)
            self._history.save_turn(session_id, message, answer)
            return {"answer": answer, "sources": []}

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
            self._history.save_turn(session_id, message, answer)
            return {"answer": answer, "sources": []}

        sources = self._extract_sources(response)
        self._history.save_turn(session_id, message, answer, sources=sources)
        return {"answer": answer, "sources": sources}

    async def chat_stream(
        self,
        session_id: str,
        message: str,
        collection: Literal["experiences", "advice", "both"] = "both",
        sources_out: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        flagged, is_new_flag = await self._check_safety(session_id, message)
        if flagged:
            if is_new_flag:
                # Deterministic, unmodified text for the highest-stakes moment — the
                # initial disclosure never depends on model output.
                full_text = SAFETY_RESOURCES_RESPONSE
                yield full_text
            else:
                messages = self._build_safety_messages(session_id, message)
                stream = await LlamaSettings.llm.astream_chat(messages)
                full_text = ""
                async for chunk in stream:
                    if chunk.delta:
                        full_text += chunk.delta
                        yield chunk.delta
                if not full_text:
                    full_text = SAFETY_RESOURCES_RESPONSE
                    yield full_text
            self._update_memory(session_id, message, full_text)
            self._history.save_turn(session_id, message, full_text)
            return

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
            self._history.save_turn(session_id, message, full_text)
        else:
            engine = self._build_chat_engine(session_id, collection)
            streaming_response = await engine.astream_chat(message)
            full_text = ""
            async for token in streaming_response.async_response_gen():
                full_text += token
                yield token
            sources = self._extract_sources(streaming_response)
            if sources_out is not None:
                sources_out.extend(sources)
            self._history.save_turn(session_id, message, full_text, sources=sources)
