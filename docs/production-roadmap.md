# happy-wife-gpt — Production Roadmap

> Path from "works on my laptop" to "deployed on AWS with proper security."

---

## Current State

| Area | Status | Notes |
|---|---|---|
| FastAPI backend | ✅ Complete | Auth, sessions, chat streaming, ingest, delete |
| React frontend | ✅ Complete | Chat UI, slide-in document panel, pink/purple theme |
| RAG engine | ✅ Complete | LlamaIndex + gpt-4o-mini + text-embedding-3-small |
| ChromaDB (local) | ✅ Complete | `experiences` + `advice` collections, cosine HNSW |
| X-API-Key auth | ✅ Complete | Disabled when `API_KEY` unset (local dev convenience) |
| Docker Compose | ✅ Complete | Backend + frontend, local dev |
| Tests | ✅ Complete | 42 passing, fully mocked, no API keys needed |
| OpenSearch backend | ⚠️ Stub | Three methods raise `NotImplementedError` |
| S3 storage backend | ❌ Missing | Not implemented |
| Persistent chat history | ✅ Complete | SQLite locally (`ChatHistoryStore`); RDS Postgres still pending for AWS (Phase D below) |
| IPV/abuse safety gate | ✅ Complete | Keyword + LLM classifier routes to hotline resources instead of conflict coaching, see `docs/rag-architecture.md` §2 |
| Production auth | ❌ Missing | Need strong key + rate limiting at minimum |
| AWS infrastructure | ❌ Missing | All to be built |
| CI/CD pipeline | ❌ Missing | GitHub Actions workflows to be created |
| Monitoring | ❌ Missing | CloudWatch, alerting |

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

## Part 2 — Security Hardening (do before AWS)

Complete these locally first — they cost nothing and reduce risk immediately.

### 2.1 Generate a real API key

```bash
openssl rand -hex 32
# → e.g. a3f9c2d1e8b74f0...
```

Add to `.env`:
```
API_KEY=a3f9c2d1e8b74f0...
```

Add to `frontend/.env` (so the React app sends it):
```
VITE_API_KEY=a3f9c2d1e8b74f0...
```

> ⚠️ The OpenAI API key was briefly saved in `.env.example` during development. If you haven't already, rotate it at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

### 2.2 Rate limiting

Add `slowapi` to `backend/requirements.txt` and wire it into `backend/main.py`:

```python
# ~20 chat requests / minute per IP (personal use)
# ~10 ingest requests / minute per IP
```

This prevents accidental (or intentional) runaway API costs.

### 2.3 Input length limits

Add `max_length=4000` to `ChatRequest.message` in `backend/models/schemas.py` to prevent
prompt injection via extremely long inputs.

### 2.4 CORS lockdown

Before deploying, change `CORS_ORIGINS` in `.env` from `localhost:5173` to your production
domain only:
```
CORS_ORIGINS=["https://yourdomain.com"]
```

---

## Part 3 — AWS Infrastructure

### Architecture

```
Internet
    │
    ▼
CloudFront  (CDN + HTTPS via ACM)
    ├── /*          →  S3 bucket (React frontend build)
    └── /api/*      →  Application Load Balancer
                            │
                            ▼
                    ECS Fargate  (backend Docker container)
                        ├── AWS Secrets Manager  (API keys, DB creds)
                        ├── RDS PostgreSQL        (chat history)
                        ├── OpenSearch Serverless (vector store)
                        └── S3 bucket            (uploaded documents)
```

### Phase A — Container & ECR (1–2 hours)

```bash
# Create ECR repository
aws ecr create-repository --repository-name happy-wife-gpt --region ap-southeast-1

# Build and push
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker build -t happy-wife-gpt ./backend
docker tag happy-wife-gpt:latest $ECR_URI/happy-wife-gpt:latest
docker push $ECR_URI/happy-wife-gpt:latest
```

Verify the container starts with env vars injected from Secrets Manager before moving on.

### Phase B — ECS Fargate backend (~half day)

1. Create ECS cluster (`happy-wife-gpt-cluster`)
2. Task definition:
   - CPU: 0.5 vCPU, Memory: 1 GB (sufficient for personal use)
   - Image: ECR URI above
   - Log driver: `awslogs` → CloudWatch log group `/ecs/happy-wife-gpt`
   - Env vars: sourced from Secrets Manager (not hardcoded in task def)
3. Service: 1 desired task, ALB target group, health check `GET /health`
4. Security group: allow 8000 from ALB only; no public inbound

### Phase C — OpenSearch Serverless (vector store) (~2 hours)

1. Create collection (type: `vectorSearch`, name: `happy-wife-gpt`)
2. Create data access policy allowing ECS task role
3. Implement `backend/storage/opensearch.py`:
   - `get_store(collection)` → `OpensearchVectorStore` (LlamaIndex adapter)
   - `list_documents(collection)` → query `_search` with metadata filter
   - `delete_document(doc_id, collection)` → delete by `doc_id` metadata
4. Set env vars:
   ```
   VECTOR_STORE_BACKEND=opensearch
   OPENSEARCH_ENDPOINT=https://xxxx.ap-southeast-1.aoss.amazonaws.com
   ```

> **Cost note:** OpenSearch Serverless has a ~$24/month minimum (0.5 OCU).
> **Alternative:** Keep ChromaDB on ECS with an EFS volume (`/chroma_db` → EFS mount).
> This saves ~$24/month and requires zero code changes — just mount the EFS in the task def.
> Recommended for personal use until traffic justifies OpenSearch.

### Phase D — RDS PostgreSQL (persistent chat history) (~2 hours)

1. Create `db.t4g.micro` RDS PostgreSQL instance (20 GB gp3)
2. VPC: same as ECS, private subnet, no public access
3. Schema:
   ```sql
   CREATE TABLE chat_sessions (
     session_id  UUID PRIMARY KEY,
     created_at  TIMESTAMPTZ DEFAULT now()
   );
   CREATE TABLE chat_messages (
     id          BIGSERIAL PRIMARY KEY,
     session_id  UUID REFERENCES chat_sessions(session_id),
     role        TEXT NOT NULL,   -- 'user' | 'assistant' | 'system'
     content     TEXT NOT NULL,
     created_at  TIMESTAMPTZ DEFAULT now()
   );
   ```
4. Implement `backend/storage/chat_history.py`:
   - `load_history(session_id)` → returns `list[ChatMessage]`
   - `save_turn(session_id, user_msg, assistant_msg)` → inserts two rows
5. Wire into `RAGEngine._get_memory()` to load from DB on first call, persist after each turn
6. Add to `.env`: `DATABASE_URL=postgresql://user:pass@host:5432/happywifegpt`

### Phase E — S3 file storage (~1 hour)

1. Create S3 bucket: `happy-wife-gpt-documents-[account-id]`
2. Implement `backend/storage/s3.py`:
   - `save_upload(file_bytes, filename, collection)` → `s3.put_object(...)`
   - Files stored at `s3://bucket/{collection}/{doc_id}/{filename}`
3. Set env vars:
   ```
   STORAGE_BACKEND=s3
   S3_BUCKET=happy-wife-gpt-documents-xxxx
   ```

### Phase F — Frontend: CloudFront + S3 (~1 hour)

```bash
# Build
cd frontend && npm run build

# Create S3 bucket for static hosting
aws s3 mb s3://happy-wife-gpt-frontend --region ap-southeast-1

# Upload
aws s3 sync dist/ s3://happy-wife-gpt-frontend --delete

# CloudFront distribution
# - Origin 1: S3 bucket (/* → frontend)
# - Origin 2: ALB (api.yourdomain.com → backend)
# - ACM cert for yourdomain.com (request in us-east-1 for CloudFront)
# - Route 53: yourdomain.com → CloudFront distribution
```

Frontend env vars at build time:
```
VITE_API_URL=https://api.yourdomain.com
VITE_API_KEY=[production key from Secrets Manager]
```

---

## Part 4 — CI/CD (GitHub Actions)

### `.github/workflows/backend.yml`

Triggers on push to `main` when files under `backend/` change.

```yaml
steps:
  - Run pytest tests/           # gate: must pass before build
  - docker build backend/
  - Push to ECR
  - aws ecs update-service --force-new-deployment --cluster happy-wife-gpt-cluster --service happy-wife-gpt-svc
```

### `.github/workflows/frontend.yml`

Triggers on push to `main` when files under `frontend/` change.

```yaml
steps:
  - npm ci && npm run build     # gate: must pass
  - aws s3 sync dist/ s3://$S3_FRONTEND_BUCKET --delete
  - aws cloudfront create-invalidation --distribution-id $CF_DIST_ID --paths "/*"
```

### GitHub Actions secrets needed

| Secret | Value |
|---|---|
| `AWS_ROLE_ARN` | IAM role ARN (OIDC — preferred over static keys) |
| `ECR_REGISTRY` | `123456789.dkr.ecr.ap-southeast-1.amazonaws.com` |
| `ECS_CLUSTER` | `happy-wife-gpt-cluster` |
| `ECS_SERVICE` | `happy-wife-gpt-svc` |
| `S3_FRONTEND_BUCKET` | `happy-wife-gpt-frontend` |
| `CF_DISTRIBUTION_ID` | CloudFront distribution ID |

Use **OIDC federation** (not static `AWS_ACCESS_KEY_ID`) — safer, no key rotation needed.

---

## Part 5 — Production Hardening Checklist

| # | Concern | Solution | Priority |
|---|---|---|---|
| 1 | HTTPS everywhere | CloudFront + ACM (free certs) | 🔴 Must |
| 2 | No secrets in code | AWS Secrets Manager for all keys | 🔴 Must |
| 3 | DB backups | RDS automated backups, 7-day retention | 🔴 Must |
| 4 | Cost guardrail | AWS Budget alert at $50/month → email | 🔴 Must |
| 5 | Rate limiting | `slowapi` in FastAPI (chat: 20/min, ingest: 10/min) | 🟠 High |
| 6 | Logging | CloudWatch Logs via ECS awslogs driver | 🟠 High |
| 7 | Health alerts | CloudWatch Alarm on 5xx rate → SNS → email | 🟠 High |
| 8 | Zero-downtime deploys | ECS rolling update (built-in default) | 🟢 Built-in |
| 9 | WAF | AWS WAF on CloudFront (rate limiting, geo) | 🟡 Medium |
| 10 | Secret rotation | Secrets Manager auto-rotate for DB password | 🟡 Medium |
| 11 | VPC isolation | Backend + RDS in private subnet, no public IP | 🔴 Must |

---

## Part 6 — Cost Estimate (ap-southeast-1, personal use)

### Option A — Full AWS (OpenSearch)

| Service | Spec | Est. monthly |
|---|---|---|
| ECS Fargate | 0.5 vCPU / 1 GB / ~8 hrs/day | ~$5 |
| RDS PostgreSQL | db.t4g.micro, 20 GB gp3 | ~$15 |
| OpenSearch Serverless | 0.5 OCU minimum | ~$24 |
| S3 + CloudFront | Low traffic | <$2 |
| Secrets Manager | 3 secrets | ~$1 |
| ALB | 1 instance | ~$18 |
| **Total** | | **~$65/month** |

### Option B — Lean AWS (ChromaDB on EFS) — recommended to start

| Service | Spec | Est. monthly |
|---|---|---|
| ECS Fargate | 0.5 vCPU / 1 GB / ~8 hrs/day | ~$5 |
| RDS PostgreSQL | db.t4g.micro, 20 GB gp3 | ~$15 |
| EFS (ChromaDB storage) | ~1 GB | ~$0.30 |
| S3 + CloudFront | Low traffic | <$2 |
| Secrets Manager | 3 secrets | ~$1 |
| ALB | 1 instance | ~$18 |
| **Total** | | **~$41/month** |

> Start with Option B. Migrate to OpenSearch only if you need multi-instance scaling
> (unlikely for a personal tool) or if EFS performance becomes a concern.

---

## Recommended Order of Work

```
[ ] 1. Write and ingest 5–10 experience entries  ← unblocks useful RAG immediately
[ ] 2. Generate and set a real API_KEY in .env
[ ] 3. Add rate limiting (slowapi)
[ ] 4. Add input length validation to ChatRequest
[ ] 5. Implement persistent chat history (SQLite first, then RDS)
[ ] 6. Set up AWS account + billing alerts
[ ] 7. Phase A — ECR + test container locally
[ ] 8. Phase B — ECS Fargate backend
[ ] 9. Phase D — RDS PostgreSQL (chat history)
[ ] 10. Phase E — S3 file storage
[ ] 11. Phase F — CloudFront + frontend deploy
[ ] 12. GitHub Actions CI/CD
[ ] 13. CloudWatch logging + alerts
[ ] 14. Phase C — OpenSearch (optional, defer until needed)
```
