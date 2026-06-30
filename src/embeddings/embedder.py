"""
Stage 3: Embedding
Convert text chunks into dense vectors using OpenAI's embedding model.
These vectors capture semantic meaning — similar text has similar vectors.
"""

import os
from openai import OpenAI

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def embed_texts(
    texts: list[str],
    model: str = "text-embedding-3-small",
    batch_size: int = 100,
) -> list[list[float]]:
    """Embed a list of texts, batching to respect API limits."""
    client = _get_client()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(input=batch, model=model)
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


def embed_query(query: str, model: str = "text-embedding-3-small") -> list[float]:
    return embed_texts([query], model=model)[0]
