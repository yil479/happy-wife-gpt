from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ingestion.loader import load_directory
from src.ingestion.chunker import chunk_documents
from src.embeddings.embedder import embed_texts
from src.vectorstore.store import add_chunks
from src.retrieval.retriever import retrieve
from src.generation.generator import generate_answer

router = APIRouter()


class IngestRequest(BaseModel):
    directory: str
    collection_name: str = "rag_docs"
    chunk_size: int = 512
    chunk_overlap: int = 64


class QueryRequest(BaseModel):
    query: str
    collection_name: str = "rag_docs"
    n_results: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]


@router.post("/ingest")
def ingest(req: IngestRequest) -> dict:
    """Load documents from a directory, chunk them, embed, and store."""
    docs = load_directory(req.directory)
    if not docs:
        raise HTTPException(status_code=400, detail="No documents found in directory")

    chunks = chunk_documents(docs, chunk_size=req.chunk_size, chunk_overlap=req.chunk_overlap)
    embeddings = embed_texts([c["text"] for c in chunks])
    add_chunks(chunks, embeddings, collection_name=req.collection_name)

    return {"status": "ok", "docs_loaded": len(docs), "chunks_stored": len(chunks)}


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    """Retrieve relevant chunks and generate an answer."""
    chunks = retrieve(req.query, n_results=req.n_results, collection_name=req.collection_name)
    answer = generate_answer(req.query, chunks)
    sources = [{"text": c["text"][:200], "score": round(c["score"], 3), **c["metadata"]} for c in chunks]
    return QueryResponse(answer=answer, sources=sources)


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
