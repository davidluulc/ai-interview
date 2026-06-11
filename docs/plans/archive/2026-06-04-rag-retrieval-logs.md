# RAG Retrieval Logs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a focused RAG retrieval logging system so question/report generation records which retrievers ran, what they hit, and whether the context entered the prompt.

**Architecture:** Create `RagRetrievalLog` as a database-backed observability table, add a small logging service, write logs inside `/api/interview/next-question` and `/api/interview/report`, and expose authenticated recent-log/debug endpoints under `/api/rag/logs`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, pytest.

---

### Task 1: Tests First

**Files:**
- Create: `tests/test_rag_retrieval_logs.py`

- [ ] Verify unauthenticated users cannot read logs.
- [ ] Verify `/api/interview/next-question` writes logs for role knowledge, question bank, and candidate memory.
- [ ] Verify `/api/interview/report` writes logs with `requestType = report`.
- [ ] Verify users can only read their own logs.

### Task 2: Database And Service

**Files:**
- Modify: `backend_python/db_models.py`
- Create: `backend_python/rag_logging.py`
- Create: `alembic/versions/20260604_0005_add_rag_retrieval_logs.py`
- Modify: `backend_python/database.py`

- [ ] Add `rag_retrieval_logs` model and migration.
- [ ] Add SQLite compatibility table creation.
- [ ] Add helper functions to serialize hits safely and save one log per retriever.

### Task 3: Route Integration

**Files:**
- Modify: `backend_python/schemas.py`
- Modify: `backend_python/routes/interview.py`
- Modify: `backend_python/routes/rag.py`

- [ ] Add `applicationProfileId` to question/report request schemas.
- [ ] Log role knowledge, question bank, and candidate memory retrievals before prompt injection.
- [ ] Add `GET /api/rag/logs/recent` for current user.
- [ ] Add `GET /api/rag/logs/{log_id}` for current user.

### Task 4: Verification

**Commands:**
- `python -m pytest tests/test_rag_retrieval_logs.py -q`
- `python -m pytest -q`
- `node --check app.js`
