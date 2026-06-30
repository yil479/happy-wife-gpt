Review the current staged and unstaged changes in this repo for issues before committing.

Focus on:
- Correctness bugs (logic errors, off-by-ones, wrong conditions)
- Security issues (injection, exposed secrets, missing auth checks)
- API contract breaks (schema changes, renamed fields, removed endpoints)
- Missing or broken error handling at system boundaries
- Obvious performance problems (N+1 queries, unbounded loops)

Context for this project:
- Backend is Python + FastAPI + LlamaIndex. Auth is enforced via `X-API-Key` header in `backend/auth.py`.
- Two ChromaDB collections: `experiences` and `advice`. Keep them separate.
- Storage and vector store are abstracted — changes to `BaseVectorStore` interface break both `chroma.py` and `opensearch.py`.
- Pydantic schemas in `backend/models/schemas.py` are the API contract — field renames are breaking changes.
- Tests in `tests/` use mocked engine/store — a logic change may pass tests but still be wrong.

Run `git diff` and `git diff --staged`, then report findings as a short bulleted list. Rate each finding as `[critical]`, `[warning]`, or `[info]`. Skip style nits.
