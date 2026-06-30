import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from backend.config import Settings
from backend.storage.base import BaseVectorStore


def _generate_doc_id(filename: str, content: bytes) -> str:
    """Deterministic doc_id from filename stem + content hash."""
    h = hashlib.sha256(content).hexdigest()[:12]
    stem = Path(filename).stem[:32]
    return f"{stem}_{h}"


def _parse_pdf_bytes(content: bytes, metadata: dict) -> list[Document]:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    docs = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            docs.append(Document(text=text, metadata={**metadata, "page": i + 1}))
    return docs


def _parse_text_bytes(content: bytes, metadata: dict) -> list[Document]:
    text = content.decode("utf-8", errors="replace")
    return [Document(text=text, metadata=metadata)]


async def ingest_upload(
    upload,  # FastAPI UploadFile
    collection: str,
    settings: Settings,
    store: BaseVectorStore,
) -> dict:
    """Ingest a single uploaded file into the specified collection."""
    content = await upload.read()
    filename = upload.filename or "unknown"
    doc_id = _generate_doc_id(filename, content)
    ext = Path(filename).suffix.lower()

    base_metadata = {
        "doc_id": doc_id,
        "filename": filename,
        "collection": collection,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

    if ext == ".pdf":
        documents = _parse_pdf_bytes(content, base_metadata)
    else:
        documents = _parse_text_bytes(content, base_metadata)

    if not documents:
        raise ValueError(f"No extractable text found in {filename}")

    splitter = SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    vector_store = store.get_store(collection)
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

    nodes = splitter.get_nodes_from_documents(documents)
    index.insert_nodes(nodes)

    return {
        "doc_id": doc_id,
        "filename": filename,
        "collection": collection,
        "chunks_stored": len(nodes),
    }
