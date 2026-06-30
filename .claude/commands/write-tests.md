Write pytest tests for the code I describe or point you to.

Rules for this project:
- Tests live in `tests/test_chat.py` or `tests/test_ingest.py` (add a new file if the scope is clearly different).
- Use `TestClient` from `starlette.testclient` — no real API calls, no real ChromaDB.
- Mock `backend.main.get_vector_store` and `backend.main.RAGEngine` via `unittest.mock.patch` so the lifespan doesn't touch real infra.
- Mock `backend.rag.ingestion.VectorStoreIndex` in ingest tests to skip embedding calls.
- Auth: include `AUTH_HEADERS` from `tests/conftest.py` on authenticated requests; test the 401 path too.
- Fixtures: prefer the existing `client`, `mock_store`, `mock_engine` fixtures from `conftest.py`. Only add new fixtures if they're truly reusable across multiple tests.
- Each test function should test exactly one behaviour. Name tests `test_<what>_<condition>` (e.g. `test_ingest_empty_file_returns_422`).
- No mocking of things that are pure Python (e.g. `SentenceSplitter` — let it run).

Tell me what you want tested (a function, an endpoint, an edge case) and I'll write the tests.
