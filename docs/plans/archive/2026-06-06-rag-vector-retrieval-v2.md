# RAG Vector Retrieval V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add embedding storage and vector retrieval support while keeping BM25 as the default retrieval mode.

**Architecture:** Add an embedding client for DashScope `text-embedding-v4`, extend `RagChunk` with JSON-backed embedding fields, generate embeddings when RAG documents are created, and add `mode="vector"` to `RetrievalService` using cosine similarity. Existing role/question RAG flows continue to use BM25 by default.

**Tech Stack:** Python, FastAPI, SQLAlchemy, SQLite, Alembic, httpx, pytest.

---

## File Structure

- Create `backend_python/embedding_client.py`: DashScope embedding API wrapper and response parsing.
- Modify `backend_python/config.py`: add `DASHSCOPE_EMBEDDING_MODEL`.
- Modify `backend_python/db_models.py`: add embedding fields to `RagChunk`.
- Modify `backend_python/database.py`: SQLite compatibility creation and column backfill for embedding fields.
- Add Alembic migration `alembic/versions/20260606_0007_add_rag_chunk_embeddings.py`.
- Modify `backend_python/rag_store.py`: async document creation with embedding generation, serialization fields.
- Modify `backend_python/routes/rag_documents.py`: call async document creation.
- Modify `backend_python/retrieval_service.py`: add cosine similarity and vector retrieval mode.
- Add `tests/test_embedding_client.py`: embedding response parsing and key-safe error behavior.
- Add `tests/test_rag_vector_retrieval.py`: vector similarity retrieval.
- Modify `tests/test_rag_documents.py`: document creation stores embedding status.
- Modify `tests/test_database_migrations.py`: migration/model field checks.

## Task 1: Embedding Client

**Files:**
- Create: `backend_python/embedding_client.py`
- Modify: `backend_python/config.py`
- Test: `tests/test_embedding_client.py`

- [ ] Write failing tests for embedding payload and response parsing.
- [ ] Verify RED: `python -m pytest tests/test_embedding_client.py -q`
- [ ] Implement `build_embedding_payload`, `extract_embedding`, and `embed_text`.
- [ ] Verify GREEN: `python -m pytest tests/test_embedding_client.py -q`

## Task 2: Database Fields

**Files:**
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/database.py`
- Add: `alembic/versions/20260606_0007_add_rag_chunk_embeddings.py`
- Modify: `tests/test_database_migrations.py`

- [ ] Write failing tests asserting `RagChunk` has `embedding_json`, `embedding_model`, `embedding_status`.
- [ ] Verify RED: `python -m pytest tests/test_database_migrations.py -q`
- [ ] Add SQLAlchemy model fields.
- [ ] Add Alembic migration.
- [ ] Add SQLite compatibility create/backfill logic.
- [ ] Verify GREEN: `python -m pytest tests/test_database_migrations.py -q`

## Task 3: Store Embeddings During Document Creation

**Files:**
- Modify: `backend_python/rag_store.py`
- Modify: `backend_python/routes/rag_documents.py`
- Modify: `tests/test_rag_documents.py`

- [ ] Write failing test that monkeypatches embedding generation and asserts created chunks have `embeddingStatus="ready"`.
- [ ] Write failing test that embedding failure still creates chunks with `embeddingStatus="failed"`.
- [ ] Verify RED: `python -m pytest tests/test_rag_documents.py -q`
- [ ] Add async `create_rag_document_with_embeddings`.
- [ ] Keep existing sync `create_rag_document` usable for tests and fallback.
- [ ] Update route to call async creation.
- [ ] Include embedding fields in `serialize_chunk`.
- [ ] Verify GREEN: `python -m pytest tests/test_rag_documents.py -q`

## Task 4: Vector Retrieval Mode

**Files:**
- Modify: `backend_python/retrieval_service.py`
- Add: `tests/test_rag_vector_retrieval.py`

- [ ] Write failing tests for `cosine_similarity` and `retrieve_chunks(mode="vector")`.
- [ ] Verify RED: `python -m pytest tests/test_rag_vector_retrieval.py -q`
- [ ] Implement vector parsing, cosine similarity, and query embedding injection point.
- [ ] Keep `mode="bm25"` behavior unchanged.
- [ ] Verify GREEN: `python -m pytest tests/test_rag_vector_retrieval.py -q`

## Task 5: Verification

- [ ] Run focused tests:

```powershell
python -m pytest tests/test_embedding_client.py tests/test_rag_documents.py tests/test_rag_vector_retrieval.py tests/test_retrieval_service.py -q
```

- [ ] Run full backend regression:

```powershell
python -m pytest -q
```

- [ ] Run frontend smoke checks:

```powershell
node tests/frontend_rag_documents.test.mjs
node tests/frontend_rag_logs.test.mjs
node --check app.js
```

## Self-Review

- Spec coverage: Embedding client, model fields, SQLite compatibility, chunk embedding creation, vector retrieval, and regression tests are covered.
- Scope check: Hybrid search, rerank, vector database, async task queue, and candidate memory vectorization are explicitly excluded.
- Type consistency: Database columns use snake_case; serialized API fields use camelCase: `embeddingJson`, `embeddingModel`, `embeddingStatus`.
