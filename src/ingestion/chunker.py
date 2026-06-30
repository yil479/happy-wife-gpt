"""
Stage 2: Chunking
Split large documents into smaller overlapping chunks.
Chunk size and overlap are key hyperparameters — too small loses context,
too large drowns out the relevant signal.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(
    docs: list[dict],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for doc in docs:
        pieces = splitter.split_text(doc["text"])
        for i, piece in enumerate(pieces):
            chunks.append({
                "text": piece,
                "metadata": {**doc["metadata"], "chunk_index": i},
            })
    return chunks
