# happy-wife-gpt — RAG System Architecture

> A breakdown of the full pipeline: how documents are ingested, embedded, stored, retrieved, fused, and used to generate grounded responses — and how a safety gate routes signs of abuse away from ordinary conflict coaching before any of that runs.

---

## System Overview

```mermaid
flowchart LR
    subgraph Ingest["📥 Ingest Path"]
        U1(User uploads file) --> API1(POST /ingest)
        API1 --> Parse
        Parse --> Chunk
        Chunk --> Embed1(Embed chunks)
        Embed1 --> Store[(ChromaDB)]
    end

    subgraph Chat["💬 Chat Path"]
        U2(User sends message) --> API2(POST /chat)
        API2 --> Safety{🛑 Safety Gate}
        Safety -->|abuse signals detected| SafetyResp(Safety resources<br/>no RAG, no coaching)
        Safety -->|no signals| Condense
        Condense --> Embed2(Embed condensed query)
        Embed2 --> Retrieve
        Store --> Retrieve
        Retrieve --> Generate(GPT-4o-mini)
        Generate --> Response(Streaming SSE / JSON)
        SafetyResp --> Response
        Response -.->|persist turn +<br/>safety_flagged| History[(SQLite)]
    end

    OpenAI([OpenAI API]) -.->|text-embedding-3-small| Embed1
    OpenAI -.->|text-embedding-3-small| Embed2
    OpenAI -.->|gpt-4o-mini| Condense
    OpenAI -.->|gpt-4o-mini| Generate
    OpenAI -.->|gpt-4o-mini classifier| Safety
```

---

## 1. Ingestion Pipeline

How a document goes from an uploaded file to searchable vectors in ChromaDB.

```mermaid
flowchart TD
    A([User uploads file\nPOST /ingest]) --> B{Extension check}
    B -->|.txt / .md| C[UTF-8 decode\n→ 1 Document]
    B -->|.pdf| D[pypdf PdfReader\n→ 1 Document per page]
    B -->|other| ERR[❌ 400 Unsupported type]

    C --> E[Attach metadata\ndoc_id · filename · collection · ingested_at]
    D --> E

    E --> F[SentenceSplitter\nchunk_size=512 tokens\noverlap=64 tokens]
    F --> G[N chunks / nodes]

    G --> H[OpenAI API\ntext-embedding-3-small\n1536-dim vector per chunk]

    H --> I{Target collection}
    I -->|experiences| J[(ChromaDB\ncollection: experiences\nHNSW cosine index)]
    I -->|advice| K[(ChromaDB\ncollection: advice\nHNSW cosine index)]

    J --> L[✅ IngestResponse\ndoc_id · chunks_stored]
    K --> L
```

### Step-by-step

| Step | Code | Detail |
|---|---|---|
| **Upload** | `POST /ingest` | `multipart/form-data`; `collection` is a query param (`advice` default) |
| **Extension gate** | `routers/ingest.py` | Only `.txt`, `.md`, `.pdf` accepted; 400 otherwise |
| **Parse PDF** | `rag/ingestion.py → _parse_pdf_bytes` | `pypdf.PdfReader`; one `Document` per page; empty pages skipped |
| **Parse text** | `rag/ingestion.py → _parse_text_bytes` | UTF-8 decode with error replacement; single `Document` |
| **doc_id** | `_generate_doc_id()` | `{filename_stem[:32]}_{sha256(content)[:12]}` — deterministic, deduplication-safe |
| **Chunking** | `SentenceSplitter` | Sentence-aware splitting at 512-token boundaries; 64-token overlap preserves context across chunk edges |
| **Embedding** | `OpenAIEmbedding(text-embedding-3-small)` | 1536-dimensional dense vectors; called by LlamaIndex internally on `insert_nodes()` |
| **Storage** | `ChromaBackend.get_store(collection)` | Each chunk stored as: `{id, embedding, text, metadata}`; cosine HNSW index |

---

## 2. Safety Gate

Runs first, before any retrieval or the marriage-counselor persona. Distinguishes ordinary
relationship conflict (safe to coach) from signs of intimate partner violence or coercive control
(unsafe to coach — routed to hotline resources instead). Sticky per session: once a session is
flagged, it stays flagged for every subsequent turn, even if later messages don't repeat risk
language.

```mermaid
flowchart TD
    A([User message]) --> B{Session already<br/>safety_flagged in SQLite?}
    B -->|Yes| F["Safety-mode reply<br/>SAFETY_SYSTEM_PROMPT, direct LLM<br/>(no retrieval, no advice corpus)"]
    B -->|No| C{Keyword gate<br/>contains_high_risk_language}
    C -->|Match| D[flag_session_safety]
    C -->|No match| G[LLM classifier<br/>classify_abuse_risk]
    G -->|YES| D
    G -->|NO| H[Not flagged →<br/>continue to §3 Retrieval Pipeline]
    D --> E{Is this the<br/>flagging turn?}
    E -->|Yes, first time| I["Fixed SAFETY_RESOURCES_RESPONSE<br/>hard-coded text, not LLM-generated"]
    E -->|No, already flagged this turn| F
    I --> J[(chat_messages<br/>persisted, sources: empty)]
    F --> J
```

### Step-by-step

| Step | Code | Detail |
|---|---|---|
| **Sticky check** | `ChatHistoryStore.is_session_flagged()` | If the session was already flagged on a prior turn, skip straight to safety-mode reply — no keyword/LLM check needed |
| **Keyword gate** | `rag/safety.py → contains_high_risk_language()` | Deterministic regex match for explicit red flags: physical violence, weapons, threats to kill/hurt, fear of partner, sexual coercion, stalking, surveillance, isolation, financial control. Zero LLM involvement — the clearest, highest-danger disclosures never depend on model judgment |
| **LLM classifier fallback** | `rag/safety.py → classify_abuse_risk()` | Only runs if the keyword gate found nothing. One extra `gpt-4o-mini` call, given the message + last 6 turns of memory, forced to answer `YES`/`NO` against a CDC/Hotline-derived rubric — catches indirect disclosures ("he doesn't let me see my friends anymore") that keywords miss |
| **Flag + persist** | `ChatHistoryStore.flag_session_safety()` | Sets `chat_sessions.safety_flagged = 1`; sticky for the rest of the session |
| **First flagged turn** | `rag/safety.py → SAFETY_RESOURCES_RESPONSE` | A fixed, hand-written string (National DV Hotline, text line, thehotline.org, 911) — deterministic on purpose, since this is the highest-stakes single message |
| **Later flagged turns** | `rag/prompts.py → SAFETY_SYSTEM_PROMPT` | Direct LLM call (no `CondensePlusContextChatEngine`, no retrieval) with a system prompt that forbids "both sides"/de-escalation framing and forbids suggesting couples counseling — advocates specifically advise against joint counseling when abuse is present |
| **Not flagged** | — | Falls through unchanged to the normal Retrieval → Generation pipeline (§3–4) with `MARRIAGE_COUNSELOR_SYSTEM_PROMPT` |

> **Known limitation.** The keyword list is a starting point covering the CDC/Hotline categories (fear, threats, violence, coercive control, isolation, stalking, forced sex, financial control, retaliation), not an exhaustive detector — real disclosures vary widely in phrasing. The LLM classifier is the safety net for phrasing the keyword list misses, but is still probabilistic.

---

## 3. Retrieval Pipeline

Only reached when the Safety Gate (§2) does **not** flag the message. How a user's message is
turned into a vector query and matched against stored chunks.

```mermaid
flowchart TD
    A([User message\nPOST /chat]) --> B[Auth check\nX-API-Key header]
    B --> C[Load ChatMemoryBuffer\nfor session_id\n4096 token limit]

    C --> D[CondensePlusContextChatEngine\nStep 1: Condense]
    D --> E[gpt-4o-mini rewrites\nchat history + new message\n→ standalone query]

    E --> F{collection param}

    F -->|experiences or advice| G[Single VectorStoreIndex retriever\ntop_k = 5]
    F -->|both — default| H[QueryFusionRetriever\nasync, num_queries=1]

    H --> I[experiences retriever\ntop-5 cosine hits]
    H --> J[advice retriever\ntop-5 cosine hits]
    I --> K[Reciprocal Rank Fusion\nmerges + reranks\nup to 10 candidates]
    J --> K

    G --> L[Retrieved nodes]
    K --> L

    L --> M{Any nodes found?}
    M -->|Yes| N[Pass to generation]
    M -->|No — empty KB| O[⚡ Fallback:\nDirect LLM call\nno RAG context]
```

### Step-by-step

| Step | Code | Detail |
|---|---|---|
| **Session memory** | `RAGEngine._get_memory()` | `ChatMemoryBuffer` keyed by `session_id`, cached in-process; holds turn history up to 4096 tokens, evicts oldest turns when full. On cache miss (e.g. after a server restart), reseeded from `ChatHistoryStore.load_history()` — see §5b |
| **Condense** | `CondensePlusContextChatEngine` Step 1 | GPT-4o-mini rewrites `[history + message]` into a self-contained query — removes pronouns, resolves references |
| **Embed query** | `text-embedding-3-small` | Condensed query → 1536-dim vector; same model used at ingest time |
| **Single retrieval** | `VectorStoreIndex.as_retriever(similarity_top_k=5)` | Cosine similarity search in HNSW index; returns top-5 nodes with scores |
| **Fusion retrieval** | `QueryFusionRetriever(num_queries=1, use_async=True)` | Queries both collections in parallel; `num_queries=1` means no query expansion — just parallel retrieval |
| **RRF ranking** | Built into `QueryFusionRetriever` | Reciprocal Rank Fusion: score = Σ 1/(k + rank_i); merges up to 10 candidates ranked by combined score |
| **Empty fallback** | `engine.py → chat_stream / chat` | If retriever returns 0 nodes, skips `CondensePlusContextChatEngine` and calls GPT-4o-mini directly with memory + system prompt |

> **No dedicated reranker model.** RRF is the only cross-collection ranking step. A cross-encoder reranker (e.g. Cohere Rerank, `llama-index-postprocessor-cohere-rerank`) could be added as a post-retrieval step.

---

## 4. Generation Pipeline

How retrieved context is assembled into a prompt and streamed back. This is the path for
messages that pass the Safety Gate (§2) unflagged — flagged sessions skip straight to a direct
LLM call with `SAFETY_SYSTEM_PROMPT` and no retrieved chunks at all (see §2).

```mermaid
flowchart TD
    A[Retrieved chunks\n+ session memory\n+ system prompt] --> B[CondensePlusContextChatEngine\nStep 2: Generate]

    B --> C["Prompt assembly:\n① System prompt — counselor persona\n② Condensed chat history\n③ Retrieved chunks as context\n④ User message"]

    C --> D[gpt-4o-mini]

    D --> E{stream param}
    E -->|true — default| F["SSE stream\ndata: {token: '...'}\n\ndata: [DONE]"]
    E -->|false| G["JSON response\n{session_id, answer, sources[]}"]

    F --> H([Browser / client])
    G --> H

    D --> I[Source nodes extracted\ntext preview · cosine score\nfilename · collection]
    I --> G
```

### Prompt assembly (what GPT-4o-mini actually receives)

```
[SYSTEM]
You are a calm, empathetic, and neutral marriage counselor...
(full persona from rag/prompts.py)

[ASSISTANT] (prior turns from ChatMemoryBuffer)
...

[USER] (prior turns from ChatMemoryBuffer)
...

[CONTEXT] (injected by CondensePlusContextChatEngine)
--- chunk 1 (from advice, score 0.87) ---
<text of chunk>
--- chunk 2 (from experiences, score 0.81) ---
<text of chunk>
...

[USER]
<condensed standalone query>
```

### Streaming format (SSE)

```
data: {"token": "It"}

data: {"token": " sounds"}

data: {"token": " like"}
...
data: [DONE]
```

The frontend reads this via `fetch` + `ReadableStream` (not `EventSource`, which only supports GET).

---

## 5. Full End-to-End Sequence

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend<br/>(React + Vite)
    participant API as FastAPI<br/>(backend/main.py)
    participant Engine as RAGEngine<br/>(rag/engine.py)
    participant OAI as OpenAI API
    participant Chroma as ChromaDB
    participant SQLite as SQLite<br/>(chat_history.db)

    Note over User,SQLite: ── INGEST PATH ──

    User->>FE: Upload advice.pdf to "advice"
    FE->>API: POST /ingest?collection=advice
    API->>API: Parse PDF → Documents<br/>Attach metadata, doc_id
    API->>API: SentenceSplitter → N chunks
    API->>OAI: Embed N chunks<br/>(text-embedding-3-small)
    OAI-->>API: N × [1536-dim vectors]
    API->>Chroma: insert_nodes() → store vectors + metadata
    Chroma-->>API: ack
    API-->>FE: {status: ok, chunks_stored: N}
    FE-->>User: "✓ advice.pdf — N chunks indexed"

    Note over User,SQLite: ── SESSION START / RESUME (see §5b) ──

    FE->>FE: Check localStorage for saved session_id
    alt No saved session
        FE->>API: POST /sessions
        API->>SQLite: create_session(session_id)
        API-->>FE: {session_id}
        FE->>FE: Save session_id to localStorage
    else Saved session exists
        FE->>API: GET /sessions/{id}/history
        API->>SQLite: load_history(session_id)
        SQLite-->>API: prior messages[]
        API-->>FE: {messages[]}
        FE->>FE: Render restored conversation
    end

    Note over User,SQLite: ── CHAT PATH ──

    User->>FE: "We keep arguing about dishes"
    FE->>API: POST /chat {session_id, message, stream:true}
    API->>Engine: chat_stream(session_id, message, "both")
    Engine->>SQLite: is_session_flagged(session_id)?
    SQLite-->>Engine: false

    alt Safety Gate flags the message (see §2)
        Engine->>SQLite: flag_session_safety(session_id)
        Engine-->>API: fixed SAFETY_RESOURCES_RESPONSE
        Note over Engine,Chroma: No retrieval, no advice corpus
    else Not flagged — normal coaching path
        Engine->>Engine: Load ChatMemoryBuffer for session<br/>(reseeded from SQLite if not cached)
        Engine->>OAI: Condense history + message → standalone query
        OAI-->>Engine: "standalone condensed query"
        Engine->>OAI: Embed condensed query
        OAI-->>Engine: [1536-dim vector]
        par Parallel retrieval
            Engine->>Chroma: cosine search in "experiences" top-5
            Chroma-->>Engine: nodes[]
        and
            Engine->>Chroma: cosine search in "advice" top-5
            Chroma-->>Engine: nodes[]
        end
        Engine->>Engine: RRF merge → ranked candidates
        Engine->>OAI: Generate with context + memory + system prompt<br/>(gpt-4o-mini, streaming)
        loop SSE stream
            OAI-->>Engine: token
            Engine-->>API: token
            API-->>FE: data: {"token": "..."}
            FE-->>User: append token to bubble
        end
    end

    Engine->>SQLite: save_turn(session_id, message, answer)
    API-->>FE: data: [DONE]
```

### 5b. Session persistence notes

- **Reload survives.** `session_id` lives in `localStorage`, not just React state — refreshing the
  page re-fetches history from SQLite instead of starting a new conversation.
- **Restart survives.** `ChatMemoryBuffer` is an in-process cache keyed by `session_id`; on a cache
  miss (fresh process) it's reseeded from `ChatHistoryStore.load_history()`, so a backend restart
  doesn't lose conversational context either.
- **"New Conversation"** (frontend menu) calls `POST /sessions` again and overwrites the stored
  `session_id`, starting a genuinely fresh session — including a fresh (unflagged) safety state.

---

## 6. Component Reference

| Component | Implementation | Config key | Default |
|---|---|---|---|
| **LLM** | OpenAI `gpt-4o-mini` | `LLM_MODEL` | `gpt-4o-mini` |
| **Embedding model** | OpenAI `text-embedding-3-small` | `EMBEDDING_MODEL` | `text-embedding-3-small` |
| **Embedding dimensions** | 1536 | — | fixed by model |
| **Vector store (local)** | ChromaDB `PersistentClient` | `CHROMA_PERSIST_DIR` | `./chroma_db` |
| **Vector store (AWS)** | OpenSearch Serverless | `OPENSEARCH_ENDPOINT` | — |
| **Similarity metric** | Cosine (`hnsw:space=cosine`) | — | fixed |
| **Chunker** | `SentenceSplitter` | `CHUNK_SIZE` / `CHUNK_OVERLAP` | 512 / 64 |
| **Retrieval top-k** | per collection | `RETRIEVAL_TOP_K` | 5 |
| **Fusion** | `QueryFusionRetriever` + RRF | — | when collection=`both` |
| **Chat engine** | `CondensePlusContextChatEngine` | — | always (when not safety-flagged) |
| **Session memory** | `ChatMemoryBuffer`, in-process cache reseeded from SQLite | `MEMORY_TOKEN_LIMIT` | 4096 tokens |
| **Chat history store** | SQLite via stdlib `sqlite3` (`ChatHistoryStore`) | `CHAT_HISTORY_DB_PATH` | `./chat_history.db` |
| **Chat history store (AWS)** | RDS PostgreSQL (planned, not built) | — | see `docs/production-roadmap.md` Phase D |
| **Safety detection** | Regex keyword gate + `gpt-4o-mini` classifier fallback (`rag/safety.py`) | — | hybrid, sticky per session |
| **Safety response** | Fixed hotline referral text; no couples-counseling suggestion | — | hard-coded, not LLM-generated |
| **Collections** | `experiences`, `advice` | — | two separate HNSW indexes |
| **Doc ID scheme** | `{stem[:32]}_{sha256[:12]}` | — | deterministic |
| **Supported file types** | `.txt`, `.md`, `.pdf` | — | hardcoded |

---

## 7. Two-Collection Design

```
ChromaDB
├── experiences    ← personal argument logs, emotional context, resolutions
│     hnsw:cosine
│     chunks: [text, embedding, doc_id, filename, collection, ingested_at, page?]
│
└── advice         ← marriage guidance articles, books, resources
      hnsw:cosine
      chunks: [text, embedding, doc_id, filename, collection, ingested_at, page?]
```

When `collection=both` (default in chat), both indexes are searched in parallel and results are merged via RRF. The source `collection` field is preserved in each returned chunk so the LLM (and UI) can distinguish where each piece of context came from.

---

## 8. Honest Gaps (not yet implemented)

| Gap | Where it would go | Notes |
|---|---|---|
| **Cross-encoder reranker** | Post-retrieval step in `_build_retriever()` | e.g. Cohere Rerank or `llama-index-postprocessor-cohere-rerank`; would improve precision especially for `both` collection queries |
| **Score threshold filtering** | `_build_retriever()` or as a node postprocessor | `MIN_SCORE=0.3` exists in config but is not wired into the retriever |
| **Hybrid search** | Replace `VectorStoreIndex` retriever with a hybrid retriever | Combine keyword (BM25) + vector for better lexical recall |
| **Query expansion** | `QueryFusionRetriever(num_queries > 1)` | Set `num_queries=3` to generate multiple phrasings of the query; improves recall at cost of latency + API tokens |
| **Metadata filtering** | `retriever.retrieve(query, filters=...)` | e.g. filter by date range, collection, or doc_id |
| **Safety keyword coverage** | `rag/safety.py → _HIGH_RISK_PATTERNS` | Starting-point list, not exhaustive — see the limitation note in §2 |
| **Safety classifier cost/latency control** | `rag/engine.py → _check_safety()` | Every unflagged message pays one extra `gpt-4o-mini` call when the keyword gate finds nothing; no caching or batching yet |
| **Chat history on RDS Postgres** | `storage/chat_history_postgres.py` (not built) | Local SQLite only today; AWS path documented but unimplemented — see `docs/production-roadmap.md` Phase D |
