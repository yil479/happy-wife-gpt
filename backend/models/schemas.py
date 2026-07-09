from typing import Literal
from pydantic import BaseModel, Field


# --- Shared ---

class SourceChunk(BaseModel):
    text: str
    score: float
    source: str
    collection: str


# --- Sessions ---

class SessionResponse(BaseModel):
    session_id: str


class ChatHistoryMessage(BaseModel):
    role: str
    content: str
    created_at: str
    sources: list[SourceChunk] = []


class SessionHistoryResponse(BaseModel):
    messages: list[ChatHistoryMessage]


# --- Ingest ---

class IngestResponse(BaseModel):
    status: str
    doc_id: str
    filename: str
    collection: str
    chunks_stored: int


class DocumentMeta(BaseModel):
    doc_id: str
    filename: str
    collection: str
    ingested_at: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentMeta]


# --- Chat ---

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="UUID identifying the conversation session")
    message: str = Field(..., min_length=1, max_length=4000)
    collection: Literal["experiences", "advice", "both"] = "both"
    stream: bool = True


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceChunk]
