# happy-wife-gpt — CLAUDE.md

## Project Overview

A RAG-powered marriage guidance chatbot. The user logs personal argument experiences and ingests online marriage advice. During cool-down periods after disagreements, they chat with the assistant for an initial, empathetic consultation grounded in that knowledge base.

## Tech Stack

| Layer | Local | AWS (future) |
|---|---|---|
| Frontend | React + TypeScript (Vite) | CloudFront + S3 |
| Backend | Python + FastAPI + uvicorn | ECS Fargate (same Docker image) |
| RAG framework | LlamaIndex | same |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) | same |
| Embeddings | OpenAI `text-embedding-3-small` | same |
| Vector store | ChromaDB (local file) | OpenSearch Serverless |
| File storage | Local `data/` folder | S3 |
| Chat history | SQLite | RDS PostgreSQL |
| Secrets | `.env` file | AWS Secrets Manager |

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
│   │   ├── chroma.py           # ChromaDB implementation (local)
│   │   └── opensearch.py       # OpenSearch implementation (AWS)
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
All infrastructure choices are abstracted behind interfaces so swapping local → AWS is a config change, not a rewrite:
- `VECTOR_STORE=chromadb` locally → `VECTOR_STORE=opensearch` on AWS
- `STORAGE=local` locally → `STORAGE=s3` on AWS
- Same Docker image runs locally (docker-compose) and on ECS Fargate

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

# AWS (only needed when backends are set to aws values)
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

## AWS Migration Path

When ready to move to AWS:
1. Push Docker image to ECR
2. Deploy backend to ECS Fargate
3. Build frontend → upload to S3 → serve via CloudFront
4. Swap `.env` vars: `VECTOR_STORE_BACKEND=opensearch`, `STORAGE_BACKEND=s3`
5. Move secrets to AWS Secrets Manager

No code changes required — only config.

## Persona & Tone (System Prompt)

The assistant should behave as a calm, empathetic, neutral marriage counselor:
- Validate both perspectives without taking sides
- Surface relevant past experiences from the knowledge base
- Suggest de-escalation strategies grounded in the advice corpus
- Never prescribe — frame responses as "things to consider"
- Keep responses concise; the user is likely emotionally activated
