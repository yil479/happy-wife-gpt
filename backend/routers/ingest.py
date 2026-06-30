from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from backend.auth import require_api_key
from backend.models.schemas import DocumentListResponse, DocumentMeta, IngestResponse
from backend.rag.ingestion import ingest_upload

router = APIRouter(tags=["documents"], dependencies=[Depends(require_api_key)])

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    collection: Literal["experiences", "advice"] = Query("advice"),
):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    settings = request.app.state.settings
    store = request.app.state.store

    try:
        result = await ingest_upload(file, collection, settings, store)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return IngestResponse(status="ok", **result)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    request: Request,
    collection: Literal["experiences", "advice", "both"] = Query("both"),
):
    store = request.app.state.store

    if collection == "both":
        raw = store.list_documents("experiences") + store.list_documents("advice")
    else:
        raw = store.list_documents(collection)

    docs = [DocumentMeta(**d) for d in raw]
    return DocumentListResponse(documents=docs)


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    request: Request,
    collection: Literal["experiences", "advice"] = Query(...),
):
    store = request.app.state.store
    deleted = store.delete_document(doc_id, collection)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{collection}'")
    return {"status": "deleted", "doc_id": doc_id}
