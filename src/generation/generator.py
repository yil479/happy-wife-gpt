"""
Stage 6: Generation
Pass the retrieved chunks + user question to Claude and get an answer.
The system prompt instructs the model to stay grounded in the context
and admit when it doesn't know — this reduces hallucination.
"""

import os
import anthropic

_client: anthropic.Anthropic | None = None

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context.

Rules:
- Answer using ONLY the information in the context below.
- If the context doesn't contain enough information to answer, say so clearly.
- Quote or reference specific parts of the context when relevant.
- Be concise and direct."""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def generate_answer(
    query: str,
    context_chunks: list[dict],
    model: str = "claude-haiku-4-5-20251001",
) -> str:
    if not context_chunks:
        return "I couldn't find any relevant information to answer your question."

    context = "\n\n---\n\n".join(
        f"[Source: {c['metadata'].get('source', 'unknown')}]\n{c['text']}"
        for c in context_chunks
    )

    response = _get_client().messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            }
        ],
    )
    return response.content[0].text
