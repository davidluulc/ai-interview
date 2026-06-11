# RAG Document Management V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build authenticated RAG document and chunk management, then make role/question RAG retrieval use database chunks before static seed fallback.

**Architecture:** Add `RagDocument` and `RagChunk` SQLAlchemy models with an Alembic migration and SQLite compatibility creation. Add a focused `rag_documents` route for CRUD and a `rag_store` service for chunking, serialization, and keyword retrieval. Keep existing JSON seed retrieval as fallback when database chunks do not match.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Alembic, pytest, existing JWT auth.

---

### Task 1: Document API Tests

**Files:**
- Create: `tests/test_rag_documents.py`

- [ ] Write tests for authentication, document CRUD, chunk generation, and user isolation.
- [ ] Run `python -m pytest tests/test_rag_documents.py -q` and confirm the tests fail because routes/models do not exist yet.

### Task 2: Models And Migration

**Files:**
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/database.py`
- Create: `alembic/versions/20260604_0006_add_rag_documents.py`

- [ ] Add `RagDocument` and `RagChunk` models.
- [ ] Add relationships from `User` to `rag_documents` and `rag_chunks`.
- [ ] Add SQLite compatibility table creation for local development.
- [ ] Add Alembic migration for production-style schema history.
- [ ] Run `python -m pytest tests/test_rag_documents.py -q` and confirm route failures remain while model import errors are gone.

### Task 3: RAG Store Service

**Files:**
- Create: `backend_python/rag_store.py`
- Modify: `tests/test_rag_documents.py`

- [ ] Implement paragraph-based chunking.
- [ ] Implement keyword extraction.
- [ ] Implement document serialization and chunk serialization.
- [ ] Implement database chunk keyword retrieval.
- [ ] Run `python -m pytest tests/test_rag_documents.py -q` and confirm service-level behavior is available.

### Task 4: RAG Document Routes

**Files:**
- Create: `backend_python/routes/rag_documents.py`
- Modify: `backend_python/main.py`

- [ ] Add `GET /api/rag/documents`.
- [ ] Add `POST /api/rag/documents`.
- [ ] Add `GET /api/rag/documents/{document_id}`.
- [ ] Add `DELETE /api/rag/documents/{document_id}`.
- [ ] Register the router in `main.py`.
- [ ] Run `python -m pytest tests/test_rag_documents.py -q` and confirm CRUD tests pass.

### Task 5: Retrieval Integration Tests

**Files:**
- Create: `tests/test_rag_database_retrieval.py`

- [ ] Test `retrieve_role_context` can return a user-owned database chunk.
- [ ] Test `retrieve_questions` can return a user-owned database chunk.
- [ ] Test seed fallback still works when no user database chunk matches.
- [ ] Run `python -m pytest tests/test_rag_database_retrieval.py -q` and confirm tests fail before integration.

### Task 6: Retrieval Integration

**Files:**
- Modify: `backend_python/rag.py`
- Modify: `backend_python/question_rag.py`
- Modify: `backend_python/routes/interview.py`
- Modify: `backend_python/routes/rag.py`

- [ ] Add optional `db` and `user_id` parameters to retrieval functions.
- [ ] Search database chunks first when `db` and `user_id` are provided.
- [ ] Keep JSON seed fallback when no database chunk matches.
- [ ] Pass `db` and `current_user.id` from interview and debug routes.
- [ ] Run `python -m pytest tests/test_rag_database_retrieval.py -q` and confirm tests pass.

### Task 7: Full Verification

**Commands:**
- `python -m pytest tests/test_rag_documents.py tests/test_rag_database_retrieval.py -q`
- `python -m pytest -q`
- `node --check app.js`
- Browser smoke test at `http://localhost:8000/`
