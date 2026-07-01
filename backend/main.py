from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.rag.engine import RAGEngine
from backend.routers.chat import router as chat_router
from backend.routers.ingest import router as ingest_router
from backend.routers.sessions import router as sessions_router
from backend.storage import get_vector_store
from backend.storage.chat_history import ChatHistoryStore

# Load settings once at module level so CORS middleware can be configured
# before the app starts (middleware must be added before first request).
_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = get_vector_store(_settings)
    history = ChatHistoryStore(_settings)
    engine = RAGEngine(settings=_settings, store=store, history=history)

    app.state.settings = _settings
    app.state.store = store
    app.state.history = history
    app.state.engine = engine

    yield


app = FastAPI(
    title="happy-wife-gpt",
    description="RAG-powered marriage guidance assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(ingest_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
