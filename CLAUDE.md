# happy-wife-gpt — CLAUDE.md

## Project Overview

A RAG-powered marriage guidance chatbot. The user logs personal argument experiences and ingests online marriage advice. During cool-down periods after disagreements, they chat with the assistant for an initial, empathetic consultation grounded in that knowledge base.

## Tech Stack

| Layer | Local | GCP (future) |
|---|---|---|
| Frontend | React + TypeScript (Vite) | Firebase Hosting |
| Backend | Python + FastAPI + uvicorn | Cloud Run (same Docker image) |
| RAG framework | LlamaIndex | same |
| LLM | OpenAI `gpt-4o-mini` | same |
| Embeddings | OpenAI `text-embedding-3-small` | same |
| Vector store | ChromaDB (local file) | ChromaDB (same file, on a GCS-mounted Cloud Run volume — not Vertex AI) |
| File storage | Local `data/` folder | Same `data/` folder, on the GCS-mounted volume — not a separate S3/GCS API backend |
| Chat history | SQLite | Same SQLite file, on the GCS-mounted volume — not Cloud SQL |
| Secrets | `.env` file | Secret Manager |

> Deliberately *not* AWS. See `docs/production-roadmap.md` for the reasoning — Cloud Run scales
> to zero and this design avoids anything billed by uptime (Cloud SQL, Vertex AI Vector Search),
> which keeps a personal/low-traffic deployment near $0/month instead of the ~$40+/month a
> managed-DB-and-vector-store setup would cost.

## Project Structure

```
happy-wife-gpt/
├── CLAUDE.md
├── docker-compose.yml          # local dev orchestration
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI app entrypoint
│   ├── config.py               # all settings loaded from env
│   ├── routers/
│   │   ├── chat.py             # POST /chat
│   │   └── ingest.py           # POST /ingest, GET /documents
│   ├── rag/
│   │   ├── engine.py           # LlamaIndex query engine setup
│   │   ├── ingestion.py        # document loading + indexing pipeline
│   │   └── prompts.py          # system prompt for marriage counselor persona
│   ├── storage/
│   │   ├── base.py             # abstract interface (upsert / query / list)
│   │   ├── chroma.py           # ChromaDB implementation (local + GCP — same file, mounted via GCS on Cloud Run)
│   │   └── opensearch.py       # OpenSearch stub, unused — GCP plan doesn't need it, see docs/production-roadmap.md
│   └── models/
│       └── schemas.py          # Pydantic request/response models
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── ChatWindow.tsx
│       │   ├── MessageBubble.tsx
│       │   └── DocumentUpload.tsx
│       ├── hooks/
│       │   └── useChat.ts
│       └── api/
│           └── client.ts       # typed API client
├── data/
│   ├── experiences/            # personal argument logs (plain text / markdown)
│   └── advice/                 # marriage advice articles (PDF / markdown)
└── tests/
    ├── test_chat.py
    └── test_ingest.py
```

## Architecture Decisions

### Portability-first design
Infrastructure choices are abstracted behind interfaces (`storage/base.py`, `config.py`'s
`Literal["local","s3"]` / `Literal["chromadb","opensearch"]`), so a backend swap is a config
change, not a rewrite — but the actual GCP plan deliberately **doesn't exercise that swap**:
- `VECTOR_STORE_BACKEND` stays `chromadb`; `STORAGE_BACKEND` stays `local`. On Cloud Run they
  point at a GCS-mounted volume instead of a container-local path — same code path, different
  disk underneath. This is what keeps the deployment near $0/month (see `docs/production-roadmap.md`).
- The `s3` / `opensearch` options exist in the type signature but have no working implementation
  and aren't part of the current deployment plan.
- Same Docker image runs locally (docker-compose) and on Cloud Run.

### Two ChromaDB collections
- `experiences` — private logs of past arguments, emotional context, resolutions
- `advice` — ingested marriage guidance articles, books, and resources

### Conversation memory
LlamaIndex `ChatMemoryBuffer` keeps the current session's context so follow-up questions are coherent.

### Streaming responses
FastAPI `StreamingResponse` + LlamaIndex streaming so the chat UI feels responsive, not laggy.

## Environment Variables

```bash
# LLM + Embeddings
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Storage backend: "local" | "s3"
STORAGE_BACKEND=local
LOCAL_DATA_DIR=./data

# Vector store backend: "chromadb" | "opensearch"
VECTOR_STORE_BACKEND=chromadb
CHROMA_PERSIST_DIR=./chroma_db

# AWS (unused — kept only because storage_backend/vector_store_backend's type signature
# still allows "s3"/"opensearch"; the actual GCP plan doesn't use these, see below)
AWS_REGION=ap-southeast-1
S3_BUCKET=
OPENSEARCH_ENDPOINT=

# App
CORS_ORIGINS=http://localhost:5173
```

## Key Commands

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev          # runs on http://localhost:5173

# Full stack (Docker Compose)
docker compose up --build

# Tests
pytest tests/
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Send a message, get a RAG-grounded reply (streaming) |
| `POST` | `/ingest` | Upload or point to documents for indexing |
| `GET` | `/documents` | List all ingested document sources |
| `DELETE` | `/documents/{id}` | Remove a document from the index |

## GCP Migration Path

When ready to move to GCP (full detail in `docs/production-roadmap.md` Part 3):
1. Push Docker image to Artifact Registry
2. Create a GCS bucket, mount it as a Cloud Run volume
3. Deploy backend to Cloud Run, env vars pointed at the mounted paths
   (`LOCAL_DATA_DIR`, `CHROMA_PERSIST_DIR`, `CHAT_HISTORY_DB_PATH`)
4. Build frontend → deploy via Firebase Hosting
5. Move secrets to Secret Manager

No backend swap needed — `VECTOR_STORE_BACKEND` and `STORAGE_BACKEND` stay `chromadb`/`local`.
Only the mount path changes, not the code path.

## Persona & Tone (System Prompt)

The assistant should behave as a calm, empathetic, neutral marriage counselor:
- Validate both perspectives without taking sides
- Surface relevant past experiences from the knowledge base
- Suggest de-escalation strategies grounded in the advice corpus
- Never prescribe — frame responses as "things to consider"
- Keep responses concise; the user is likely emotionally activated
