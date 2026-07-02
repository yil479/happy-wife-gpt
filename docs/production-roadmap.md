# happy-wife-gpt — Production Roadmap

> Path from "works on my laptop" to "deployed on GCP with proper security."
>
> **Cloud choice: GCP, not AWS.** This is a personal, low-traffic practice project, so the
> priority is genuine pay-as-you-go — not just "cheap," but $0 when nobody's using it. AWS's
> lean estimate (~$41/month, see git history for the old AWS-flavored version of this doc)
> is dominated by an ALB (~$18/mo) and RDS (~$15/mo), both billed flat by uptime regardless of
> traffic. GCP's Cloud Run scales to zero and has no per-service load-balancer fee, so the
> equivalent architecture below lands around **$0–3/month**. See "Why no managed DB / vector
> store" in Part 3 for the specific design choice that gets us there.

---

## Current State

| Area | Status | Notes |
|---|---|---|
| FastAPI backend | ✅ Complete | Auth, sessions, chat streaming, ingest, delete |
| React frontend | ✅ Complete | Chat UI, slide-in document panel, pink/purple theme |
| RAG engine | ✅ Complete | LlamaIndex + gpt-4o-mini + text-embedding-3-small |
| ChromaDB (local) | ✅ Complete | `experiences` + `advice` collections, cosine HNSW |
| X-API-Key auth | ✅ Complete | Real key generated and set in local `.env` + `frontend/.env`; enforced by default now |
| Docker Compose | ✅ Complete | Backend + frontend, local dev |
| Docker image (Cloud Run-ready) | ✅ Verified locally | `docker build -f backend/Dockerfile .` + `docker run --env-file .env` confirmed: `/health` → 200, `X-API-Key` auth enforced (401/200) |
| Tests | ✅ Complete | 47 passing, fully mocked, no API keys needed |
| Managed vector search (Vertex AI) | Not planned | Skipping — ChromaDB stays local-file-based, persisted via a Cloud Run volume mount instead. See Part 3. |
| GCS-backed file storage | Not needed as separate code | `STORAGE_BACKEND=local` keeps working as-is once `LOCAL_DATA_DIR` points at a GCS-mounted volume — no `storage/gcs.py` required for MVP |
| Persistent chat history | ✅ Complete locally | SQLite (`ChatHistoryStore`); stays on GCS-mounted volume on Cloud Run rather than moving to a managed DB (see Part 3) |
| IPV/abuse safety gate | ✅ Complete | Keyword + LLM classifier routes to hotline resources instead of conflict coaching, see `docs/rag-architecture.md` §2 |
| Rate limiting | ✅ Complete | `slowapi`, `/chat` 20/min, `/ingest` 10/min, per-IP, in-memory |
| Input length validation | ✅ Complete | `ChatRequest.message` capped at 4000 chars, min 1 |
| Production auth | ⚠️ Partial | Real key + rate limiting done; still needs a rotation strategy for GCP (Secret Manager versions) |
| GCP infrastructure | ❌ Missing | All to be built |
| CI/CD pipeline | ❌ Missing | GitHub Actions workflows to be created |
| Monitoring | ❌ Missing | Cloud Logging (free, automatic on Cloud Run) + Cloud Monitoring alerting to be configured |

---

## Part 1 — Seeding the Experiences Collection

The `experiences` ChromaDB collection is the **personal memory** of your marriage counselor.
It learns from your past arguments so it can surface relevant patterns when you chat.
**The RAG system is only as useful as the experiences you give it.**

### What to write

Each experience entry should be a `.txt` or `.md` file covering one argument or recurring
tension. Include:

- **What happened** — the surface-level trigger
- **Context** — time, stress level, what else was going on
- **What was said** — key phrases, especially ones that escalated things (paraphrased is fine)
- **Partner's reaction** — how they responded
- **Escalation point** — the moment it went from tense to bad
- **Resolution** — how it ended, how long it took to cool down
- **What worked** — de-escalation moves that helped
- **What didn't work** — phrases or behaviours that made it worse
- **Deeper insight** — in hindsight, what was it really about?

---

### Template

Save as `data/experiences/[topic].md` then upload via the UI or curl.

```markdown
## Argument: [Short title]
Date: [Month/Year]
Recurring: [Yes / No / Sometimes]

### What happened
[2–3 sentences describing the trigger]

### Context
[What else was going on — work stress, tiredness, recent tension, etc.]

### What was said
Me: "[key phrase I used]"
Partner: "[their response]"
Escalation: [the moment it turned]

### How it resolved
[How long, who initiated reconciliation, what was said]

### What worked
- [specific thing]
- [specific thing]

### What didn't work
- [specific thing]

### Insight
[One sentence — what was this really about underneath?]
```

---

### Example entry 1 — Household chores

```markdown
## Argument: Dishes left in the sink
Date: March 2025
Recurring: Yes — every 2–3 weeks

### What happened
I came home from a long day at work and the dishes from breakfast and lunch were still
in the sink, even though I'd mentioned it the day before.

### Context
I was already tired and had a deadline the next morning. The kitchen being messy felt
like proof that I was invisible.

### What was said
Me: "I've asked you twice. Do you just not care?"
Partner: [went quiet, then said] "I was going to do them after dinner."
Me: "You always say that."
Escalation: I walked away and went to another room. Partner didn't follow.

### How it resolved
We didn't speak much that evening. The next morning I apologised for the tone.
Partner apologised for not following through. We agreed to a rough kitchen rota.

### What worked
- Waiting until the next morning when I wasn't exhausted
- Apologising for tone separately from the underlying issue
- Proposing a concrete solution (rota) rather than relitigating the incident

### What didn't work
- "You always / you never" — immediately made partner defensive and shut down
- Walking away without saying why — felt like punishment to them
- Bringing it up when I was already at my emotional limit

### Insight
It wasn't really about the dishes. I felt like my needs kept being deprioritised,
and the dishes were just the most recent proof. The exhaustion amplified everything.
```

---

### Example entry 2 — Weekend plans

```markdown
## Argument: Making plans without checking
Date: January 2025
Recurring: Sometimes

### What happened
Partner agreed to have friends over on Saturday without checking with me first.
I had been looking forward to a quiet weekend to recharge.

### Context
It had been a very social month. I was running on empty and really needed downtime.
Partner didn't know how depleted I was feeling.

### What was said
Me: "You just decided that without asking me?"
Partner: "I didn't think it was a big deal — you like them."
Me: "It's not about whether I like them, it's that you didn't ask."
Escalation: I said "fine, do whatever you want" and ended the conversation.

### How it resolved
Partner cancelled the plans without being asked, which surprised me. We talked
about why I needed that weekend specifically. I hadn't communicated it clearly.

### What worked
- Partner taking initiative to resolve it without being pushed
- Me explaining the why (depletion) rather than just the what (the ask)
- Realising I hadn't actually told them I was struggling

### What didn't work
- "Fine, do whatever you want" — not true, and it shut down communication
- Assuming they should have known without me saying it

### Insight
I assumed my need for quiet time was obvious. It wasn't. Partner was being generous
with their friends and had no idea I was depleted. Communication failure on both sides.
```

---

### How to ingest

**Via the UI:** Open the document panel (⋯ menu → Upload Document), switch to `experiences`, pick your file.

**Via curl (batch ingest):**
```bash
for f in data/experiences/*.md; do
  curl -X POST "http://localhost:8000/ingest?collection=experiences" \
    -H "X-API-Key: $API_KEY" \
    -F "file=@$f"
  echo " → ingested $f"
done
```

### How many entries do you need?

| Count | Quality of RAG output |
|---|---|
| 0 | Counselor responds from gpt-4o-mini alone — good but generic |
| 3–5 | Starts surfacing patterns specific to your relationship |
| 10–20 | Strong retrieval — counselor can reference similar past situations |
| 20+ | Diminishing returns unless entries cover very different themes |

**Quality >> quantity.** A vague 3-line entry won't retrieve usefully. A specific, honest 200-word entry retrieves with high relevance.

---

## Part 2 — Security Hardening (do before deploying)

Complete these locally first — they cost nothing and reduce risk immediately.

### 2.1 Generate a real API key ✅ Done

```bash
openssl rand -hex 32
```

Set in `.env` (`API_KEY=...`) and the matching value in `frontend/.env` (`VITE_API_KEY=...`),
which is gitignored — see `.env.example` / `frontend/.env.example` for the placeholders. Auth is
now enforced by default; previously it was disabled whenever `API_KEY` was empty.

> Full git history was searched for leaked OpenAI keys before this change (all commits, all refs)
> — none found. `.env.example` has only ever contained the placeholder `your_openai_api_key_here`.

### 2.2 Rate limiting ✅ Done

`slowapi` added to `backend/requirements.txt`, wired into `backend/main.py` via
`backend/rate_limit.py`'s shared `Limiter`. `/chat` is capped at 20/min per IP, `/ingest` at
10/min per IP, in-memory (no Redis needed at this scale). Prevents accidental (or intentional)
runaway API costs.

### 2.3 Input length limits ✅ Done

`ChatRequest.message` in `backend/models/schemas.py` now has `min_length=1, max_length=4000`.

### 2.4 CORS lockdown

Before deploying, change `CORS_ORIGINS` in `.env` from `localhost:5173` to your production
domain only (Firebase Hosting default domain or a custom domain):
```
CORS_ORIGINS=["https://your-project.web.app"]
```

---

## Part 3 — GCP Infrastructure

### Why no managed DB / vector store

The single biggest cost lever for a personal, low-traffic project is avoiding **anything billed
by uptime instead of usage.** Cloud SQL (GCP's RDS equivalent) and Vertex AI Vector Search are
both fine engineering choices, but they're priced for services that actually need 24/7 uptime —
not a project used a few times a week.

Instead, this plan mounts a single GCS bucket as a **Cloud Run volume** (Cloud Storage FUSE) at
the paths the app already writes to locally: `chroma_db/`, `data/`, and the SQLite file. Because
`backend/storage/base.py` and `config.py` already abstract these as `local` / `chromadb`, **no
code changes are required** — `STORAGE_BACKEND=local` and `VECTOR_STORE_BACKEND=chromadb` keep
working unmodified, just pointed at a mounted path instead of a container-local one.

**Known limitation:** GCS FUSE doesn't provide real POSIX file locks, and SQLite relies on file
locking for writes. Set Cloud Run `max-instances=1` (fine for single-user traffic) so there's
never true concurrent access, and treat this as a personal-project tradeoff — not something to
carry into a multi-user deployment without revisiting.

If this project ever gets real concurrent traffic, revisit with:
- **Cloud SQL (Postgres)** for chat history (small `db-f1-micro` tier, ~$10–15/mo, not scale-to-zero)
- **Vertex AI Vector Search** for the vector store (managed, code work behind `BaseVectorStore`, similar to filling in the current `opensearch.py` stub)

Neither is needed for the "practice project, low traffic" goal.

### Architecture

```
Internet
    │
    ▼
Cloud Run  (backend, HTTPS built-in, scales to zero)
    ├── Secret Manager        (OPENAI_API_KEY, API_KEY)
    └── GCS bucket, mounted as a volume (Cloud Storage FUSE)
            ├── /app/chroma_db     (ChromaDB persist dir)
            ├── /app/data          (uploaded documents)
            └── chat_history.db    (SQLite)

Firebase Hosting  (React frontend build, free tier, auto HTTPS/CDN)
```

### Phase A — Container & Artifact Registry

**Local build/run verified ✅** — `docker build -t happy-wife-gpt -f backend/Dockerfile .` succeeds;
running with `--env-file .env` starts cleanly, `/health` returns 200, and `X-API-Key` auth works
(401 without key, 200 with it). The image is cloud-agnostic — same one works on Cloud Run.

Once a GCP project exists (step 6 below):

```bash
# Enable Artifact Registry, create a Docker repo
gcloud services enable artifactregistry.googleapis.com run.googleapis.com secretmanager.googleapis.com
gcloud artifacts repositories create happy-wife-gpt \
  --repository-format=docker --location=asia-southeast1

# Build and push
gcloud auth configure-docker asia-southeast1-docker.pkg.dev
docker build -t happy-wife-gpt -f backend/Dockerfile .
docker tag happy-wife-gpt asia-southeast1-docker.pkg.dev/$PROJECT_ID/happy-wife-gpt/backend:latest
docker push asia-southeast1-docker.pkg.dev/$PROJECT_ID/happy-wife-gpt/backend:latest
```

### Phase B — Cloud Run backend deploy (~1 hour)

1. Create the GCS bucket that will back persistent state:
   ```bash
   gcloud storage buckets create gs://happy-wife-gpt-state-$PROJECT_ID --location=asia-southeast1
   ```
2. Put secrets in Secret Manager:
   ```bash
   echo -n "$OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-
   echo -n "$API_KEY" | gcloud secrets create api-key --data-file=-
   ```
3. Deploy to Cloud Run with a volume mount (requires the `gen2` execution environment):
   ```bash
   gcloud run deploy happy-wife-gpt \
     --image asia-southeast1-docker.pkg.dev/$PROJECT_ID/happy-wife-gpt/backend:latest \
     --region asia-southeast1 \
     --execution-environment gen2 \
     --add-volume name=state,type=cloud-storage,bucket=happy-wife-gpt-state-$PROJECT_ID \
     --add-volume-mount volume=state,mount-path=/app/state \
     --set-secrets OPENAI_API_KEY=openai-api-key:latest,API_KEY=api-key:latest \
     --set-env-vars LOCAL_DATA_DIR=/app/state/data,CHROMA_PERSIST_DIR=/app/state/chroma_db,CHAT_HISTORY_DB_PATH=/app/state/chat_history.db \
     --max-instances 1 \
     --allow-unauthenticated
   ```
4. Verify: `curl https://<cloud-run-url>/health`, then an authenticated call with `X-API-Key`.

> `--allow-unauthenticated` is about *Cloud Run's* IAM layer (public HTTPS access) — the app's
> own `X-API-Key` check still gates every request underneath it, same as locally.

### Phase C — Vector store: skipped by design

See "Why no managed DB / vector store" above. ChromaDB stays exactly as it is, persisted via the
Phase B volume mount. Revisit with Vertex AI Vector Search only if traffic grows past what a
single Cloud Run instance + GCS-mounted disk can comfortably handle.

### Phase D — Chat history: skipped by design

Same reasoning — SQLite on the mounted volume instead of Cloud SQL. `backend/storage/chat_history.py`
needs no changes; only `CHAT_HISTORY_DB_PATH` moves.

### Phase E — File storage: no new code needed

`STORAGE_BACKEND=local` already writes to `LOCAL_DATA_DIR` — pointed at the mounted path in
Phase B, uploaded documents land in the GCS bucket automatically. `backend/storage/gcs.py` would
only be worth writing if you later want direct GCS API access (e.g. presigned URLs) instead of
the FUSE mount.

### Phase F — Frontend: Firebase Hosting (~30 min)

```bash
npm install -g firebase-tools
firebase login
firebase init hosting   # point public dir at frontend/dist, configure as SPA

cd frontend
npm run build
firebase deploy --only hosting
```

Frontend env vars at build time:
```
VITE_API_URL=https://<cloud-run-url>
VITE_API_KEY=[value from Secret Manager]
```

Firebase Hosting gives you a free `*.web.app` domain with automatic HTTPS; custom domains are
also free (just DNS + a managed cert).

---

## Part 4 — CI/CD (GitHub Actions)

### `.github/workflows/backend.yml`

Triggers on push to `main` when files under `backend/` change.

```yaml
steps:
  - Run pytest tests/                          # gate: must pass before build
  - auth via Workload Identity Federation (google-github-actions/auth)
  - docker build -f backend/Dockerfile .
  - Push to Artifact Registry
  - gcloud run deploy happy-wife-gpt --image ... --region asia-southeast1
```

### `.github/workflows/frontend.yml`

Triggers on push to `main` when files under `frontend/` change.

```yaml
steps:
  - npm ci && npm run build                    # gate: must pass
  - firebase deploy --only hosting --project $FIREBASE_PROJECT_ID
```

### GitHub Actions secrets needed

| Secret | Value |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Federation provider resource name |
| `GCP_SERVICE_ACCOUNT` | Deploy service account email |
| `GCP_PROJECT_ID` | GCP project ID |
| `GCP_REGION` | `asia-southeast1` |
| `ARTIFACT_REGISTRY_REPO` | `happy-wife-gpt` |
| `CLOUD_RUN_SERVICE` | `happy-wife-gpt` |
| `FIREBASE_PROJECT_ID` | Firebase project ID |

Use **Workload Identity Federation** (not a downloaded service-account JSON key) — same idea as
AWS OIDC, no long-lived key to rotate or leak.

---

## Part 5 — Production Hardening Checklist

| # | Concern | Solution | Priority |
|---|---|---|---|
| 1 | HTTPS everywhere | Cloud Run + Firebase Hosting both auto-provision managed certs | 🔴 Must |
| 2 | No secrets in code | Secret Manager for all keys | 🔴 Must |
| 3 | State backups | GCS Object Versioning on the state bucket (covers ChromaDB + SQLite) | 🔴 Must |
| 4 | Cost guardrail | GCP Budget alert at $10/month → email | 🔴 Must |
| 5 | Rate limiting | `slowapi` in FastAPI (chat: 20/min, ingest: 10/min) | 🟠 High |
| 6 | Logging | Cloud Logging — automatic for anything written to stdout/stderr on Cloud Run | 🟠 High |
| 7 | Health alerts | Cloud Monitoring uptime check on `/health` → alert policy → email | 🟠 High |
| 8 | Zero-downtime deploys | Cloud Run revisions + traffic splitting (built-in) | 🟢 Built-in |
| 9 | WAF / abuse protection | Cloud Armor — only relevant behind an external LB; skip for a single Cloud Run service at this scale | 🟡 Low priority here |
| 10 | Secret rotation | Secret Manager versions; manual rotation is fine at personal-project scale | 🟡 Medium |
| 11 | Concurrency safety | `max-instances=1` (see Part 3 "Why no managed DB / vector store") | 🔴 Must, given the FUSE/SQLite tradeoff |

---

## Part 6 — Cost Estimate (asia-southeast1, personal use)

### Recommended — Cloud Run + GCS-mounted ChromaDB/SQLite

| Service | Spec | Est. monthly |
|---|---|---|
| Cloud Run | scales to zero, light personal traffic | ~$0 (covered by free tier) |
| Cloud Storage | <1 GB (chroma index + docs + sqlite) | ~$0.02 |
| Secret Manager | 2 secrets, light access | ~$0 (free tier: 6 versions, 10k accesses/mo) |
| Firebase Hosting | low traffic | ~$0 (free tier) |
| Cloud Logging | <50 GB/mo | ~$0 (free tier) |
| **Total** | | **~$0–3/month** |

### If traffic grows — add a managed DB / vector store

| Service | Spec | Est. monthly |
|---|---|---|
| Cloud Run | as above | ~$0–5 |
| Cloud SQL (Postgres) | `db-f1-micro`, 10 GB | ~$10–15 |
| Vertex AI Vector Search | smallest tier | ~$20+ |
| Cloud Storage + Firebase Hosting | as above | ~$0–2 |
| **Total** | | **~$30–40/month** |

Start with the recommended option. There is no realistic scenario for a personal, low-traffic
practice project where the second table is worth it.

---

## Recommended Order of Work

```
[x] 1. Write and ingest 5–10 experience entries  ← unblocks useful RAG immediately
[x] 2. Generate and set a real API_KEY in .env
[x] 3. Add rate limiting (slowapi)
[x] 4. Add input length validation to ChatRequest
[x] 5. Implement persistent chat history (SQLite)
[x] 6. Phase A (local half) — build + verify the Docker image locally
[ ] 7. Create a GCP project, enable billing, set a budget alert
[ ] 8. Phase A (remote half) — Artifact Registry push
[ ] 9. Phase B — Cloud Run deploy with GCS-mounted volume + Secret Manager
[ ] 10. Phase F — Firebase Hosting frontend deploy
[ ] 11. GitHub Actions CI/CD (Workload Identity Federation)
[ ] 12. Cloud Monitoring uptime check + alert policy
[ ] 13. (optional, defer) Cloud SQL Postgres — only if you outgrow SQLite-on-GCS
[ ] 14. (optional, defer) Vertex AI Vector Search — only if you outgrow ChromaDB-on-GCS
```
