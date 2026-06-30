"""
Stage 1: Document Loading
Load raw documents from disk (PDF, plain text, markdown).
Each document becomes a dict with 'text' and 'metadata'.
"""

import os
from pathlib import Path
from pypdf import PdfReader


def load_text(path: str) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    return [{"text": text, "metadata": {"source": path, "type": "text"}}]


def load_pdf(path: str) -> list[dict]:
    reader = PdfReader(path)
    docs = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            docs.append({
                "text": text,
                "metadata": {"source": path, "page": i + 1, "type": "pdf"},
            })
    return docs


def load_directory(directory: str, extensions: list[str] | None = None) -> list[dict]:
    """Recursively load all supported files from a directory."""
    if extensions is None:
        extensions = [".txt", ".md", ".pdf"]

    docs = []
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            ext = Path(file).suffix.lower()
            if ext not in extensions:
                continue
            if ext == ".pdf":
                docs.extend(load_pdf(path))
            else:
                docs.extend(load_text(path))
    return docs
