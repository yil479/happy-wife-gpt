"""
Stage 5: Retrieval
Given a user query, find the most relevant chunks from the vector store.
This is where RAG quality lives — better retrieval = better answers.

Production improvements to explore:
- Hybrid search: combine vector + keyword (BM25) scores
- Re-ranking: use a cross-encoder to re-score the top-k results
- Contextual compression: trim chunks to only the relevant sentences
- Query expansion: rewrite the query before embedding
"""

from src.embeddings.embedder import embed_query
from src.vectorstore.store import query_collection


def retrieve(
    query: str,
    n_results: int = 5,
    min_score: float = 0.3,
    collection_name: str = "rag_docs",
) -> list[dict]:
    query_embedding = embed_query(query)
    results = query_collection(query_embedding, n_results=n_results, collection_name=collection_name)
    return [r for r in results if r["score"] >= min_score]
