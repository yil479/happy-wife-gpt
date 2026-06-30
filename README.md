# rag-to-riches

Learning to build a production RAG (Retrieval-Augmented Generation) system from scratch.

## The 6-Stage Pipeline

```
Documents → Chunk → Embed → Store → Retrieve → Generate → Answer
```

| Stage | File | What it does |
|---|---|---|
| 1. Load | `src/ingestion/loader.py` | Read PDFs, text, markdown from disk |
| 2. Chunk | `src/ingestion/chunker.py` | Split docs into overlapping pieces |
| 3. Embed | `src/embeddings/embedder.py` | Convert text to vectors (OpenAI) |
| 4. Store | `src/vectorstore/store.py` | Persist vectors in ChromaDB |
| 5. Retrieve | `src/retrieval/retriever.py` | Find top-k similar chunks for a query |
| 6. Generate | `src/generation/generator.py` | Answer with Claude, grounded in context |

An API layer (`src/api/`) wires all stages together via two endpoints: `POST /ingest` and `POST /query`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in ANTHROPIC_API_KEY and OPENAI_API_KEY
```

## Run the API

```bash
uvicorn src.api.main:app --reload
```

Interactive docs at `http://localhost:8000/docs`

## Quick start

**1. Ingest documents:**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"directory": "data/samples"}'
```

**2. Ask a question:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the six stages of a RAG pipeline?"}'
```

## Run tests

```bash
pytest tests/
```

## Project Structure

```
rag-to-riches/
├── src/
│   ├── ingestion/      # load + chunk
│   ├── embeddings/     # embed text → vectors
│   ├── vectorstore/    # ChromaDB interface
│   ├── retrieval/      # query → top-k chunks
│   ├── generation/     # Claude answer generation
│   └── api/            # FastAPI endpoints
├── data/samples/       # drop your documents here
├── tests/
└── requirements.txt
```

## What to learn next

- **Hybrid search** — combine vector similarity with BM25 keyword search
- **Re-ranking** — use a cross-encoder to re-score top-k results
- **Query rewriting** — use an LLM to rewrite the user's query before embedding
- **Evaluation** — measure retrieval recall and answer faithfulness (RAGAS)
- **Streaming** — stream Claude responses back to the client
- **Auth + rate limiting** — harden the API for production
