from typing import Literal
from pydantic import BaseModel, Field


# --- Sessions ---

class SessionResponse(BaseModel):
    session_id: str


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
    message: str
    collection: Literal["experiences", "advice", "both"] = "both"
    stream: bool = True


class SourceChunk(BaseModel):
    text: str
    score: float
    source: str
    collection: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceChunk]
