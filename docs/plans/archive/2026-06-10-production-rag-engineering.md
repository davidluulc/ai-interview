# Production RAG Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the AI mock interview system RAG module from a usable RAG implementation to a production-grade engineering foundation with document lifecycle, metadata filtering, retrieval quality evaluation, observability, and vector-store migration readiness.

**Architecture:** Keep the current FastAPI + SQLAlchemy + native frontend architecture. Add production RAG capability in small backend-first slices: document lifecycle and permissions first, then deduplication, query rewrite, hybrid/rerank explainability, evaluation cases, quality dashboard, and vector-store abstraction. Preserve `/api/interview/next-question` compatibility by extending retrieval internals without changing the interview response contract.

**Tech Stack:** Python, FastAPI, SQLAlchemy, SQLite compatibility schema, Pydantic, pytest, native HTML/CSS/JavaScript, Node `.mjs` frontend tests.

---

## Scope Rules

This plan implements `docs/superpowers/specs/2026-06-10-production-rag-engineering-design.md`.

Do not implement in this plan:

- LangGraph or LangChain runtime dependencies.
- React, Vue, Next.js, or frontend framework migration.
- Real cloud deployment, real Nginx config, or Docker deployment.
- Qdrant / pgvector runtime integration.
- OCR, Celery, Redis task queue, or monitoring alerting.
- Destructive RAG admin operations beyond explicit lifecycle status changes.

## File Map

Backend files likely modified:

- `backend_python/db_models.py`: add RAG document lifecycle and hash fields.
- `backend_python/database.py`: SQLite compatibility for new RAG fields.
- `backend_python/rag_store.py`: serialize lifecycle fields, hash helpers, metadata filter helpers, create document defaults.
- `backend_python/retrieval_service.py`: filter enabled/public/private documents and apply metadata filter.
- `backend_python/routes/rag_documents.py`: expose lifecycle fields and status update endpoint.
- `backend_python/rag.py`: pass role metadata filter when useful.
- `backend_python/question_rag.py`: pass question metadata filter when useful.
- `backend_python/routes/admin.py`: later expose RAG quality summaries.

Test files likely created or updated:

- `tests/test_rag_document_lifecycle.py`
- `tests/test_rag_metadata_filter.py`
- `tests/test_rag_document_dedup.py`
- `tests/test_rag_query_rewrite.py`
- `tests/test_rag_hybrid_rerank_explain.py`
- `tests/test_rag_evaluation_management.py`
- `tests/test_admin_rag_quality.py`
- Frontend `.mjs` tests only when a visible UI changes.

Learning docs to create:

- `docs/learning/17-RAG文档生命周期和权限边界.md`
- `docs/learning/18-RAG文档去重和chunk统计.md`
- `docs/learning/19-query-rewrite和multi-query检索.md`
- `docs/learning/20-hybrid权重和rerank解释.md`
- `docs/learning/21-RAG评测case和质量指标.md`
- `docs/learning/22-低质量召回日志和后台质量面板.md`
- `docs/learning/23-向量库持久化迁移设计.md`

Progress file:

- `docs/pre-deployment-progress.md`

---

## Task 1: RAG Document Lifecycle And Visibility

**Learning point before coding:** 生产级 RAG 的第一步不是换向量库，而是让知识库文档有生命周期和权限边界。`enabled` 文档参与检索，`disabled/archived` 文档不参与检索；`private` 文档只属于 owner，`public` 文档可以被其他用户检索。

**Files:**
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/database.py`
- Modify: `backend_python/rag_store.py`
- Modify: `backend_python/retrieval_service.py`
- Modify: `backend_python/routes/rag_documents.py`
- Test: `tests/test_rag_document_lifecycle.py`

- [ ] **Step 1: Write failing lifecycle tests**

Create `tests/test_rag_document_lifecycle.py` with tests for:

```text
disabled document is not retrieved
public document is retrieved by another user
private document is not retrieved by another user
document API returns status and visibility
```

- [ ] **Step 2: Run failing lifecycle tests**

Run:

```powershell
python -m pytest tests/test_rag_document_lifecycle.py -q
```

Expected:

```text
Tests fail because RagDocument.status / visibility and lifecycle filtering are missing.
```

- [ ] **Step 3: Add model fields and SQLite compatibility**

Add:

```text
RagDocument.status default enabled
RagDocument.visibility default private
```

For SQLite compatibility, add missing columns and indexes in `ensure_sqlite_compatibility_schema()`.

- [ ] **Step 4: Serialize lifecycle fields**

Update `serialize_document()` to return:

```text
status
visibility
```

Update `create_rag_document_with_embeddings()` and `create_rag_document()` to accept status/visibility with safe defaults.

- [ ] **Step 5: Filter retrieval by status and visibility**

Update `retrieve_chunks()` and vector retrieval paths so a user can retrieve:

```text
own enabled private documents
enabled public documents
```

And cannot retrieve:

```text
disabled documents
archived documents
other users' private documents
```

- [ ] **Step 6: Add status update endpoint**

Add a minimal endpoint:

```text
PATCH /api/rag/documents/{document_id}/status
```

Payload:

```json
{
  "status": "disabled"
}
```

Only the owner can update their own document in this stage.

- [ ] **Step 7: Run lifecycle tests**

Run:

```powershell
python -m pytest tests/test_rag_document_lifecycle.py -q
```

Expected:

```text
All lifecycle tests pass.
```

---

## Task 2: Metadata Filter

**Learning point before coding:** metadata filter 让 RAG 不只是“相似就召回”，而是先按岗位、阶段、难度、分类过滤候选范围，再做 BM25/vector/hybrid/rerank 排序。

**Files:**
- Modify: `backend_python/rag_store.py`
- Modify: `backend_python/retrieval_service.py`
- Modify: `backend_python/rag.py`
- Modify: `backend_python/question_rag.py`
- Test: `tests/test_rag_metadata_filter.py`

- [ ] **Step 1: Write failing metadata filter tests**

Create tests proving:

```text
positionTag filter keeps matching chunks
positionTag filter excludes mismatched chunks
category filter works
difficulty filter works for question bank
metadata filter is recorded in hit metadata
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
python -m pytest tests/test_rag_metadata_filter.py -q
```

- [ ] **Step 3: Implement filter helpers**

Add helpers:

```text
normalize_metadata_filter
chunk_matches_metadata_filter
```

Supported fields:

```text
positionTag
category
difficulty
interviewStage
source
```

- [ ] **Step 4: Thread metadata_filter through retrieval**

Add `metadata_filter` parameter to:

```text
retrieve_chunks
retrieve_vector_chunks
retrieve_hybrid_chunks
retrieve_hybrid_rerank_chunks
retrieve_role_context
retrieve_questions
```

- [ ] **Step 5: Run metadata tests and route regression**

Run:

```powershell
python -m pytest tests/test_rag_metadata_filter.py tests/test_interview_agent_route.py -q
```

---

## Task 3: Document And Chunk Deduplication

**Learning point before coding:** 生产级知识库不能只会新增文档，还要能识别重复文档和重复 chunk，否则知识库越用越脏，召回质量会下降。

**Planned files:**
- `backend_python/db_models.py`
- `backend_python/database.py`
- `backend_python/rag_store.py`
- `tests/test_rag_document_dedup.py`
- `docs/learning/18-RAG文档去重和chunk统计.md`

Deliverables:

```text
content_hash
chunk_hash
duplicateChunkCount
document detail stats
```

---

## Task 4: Query Rewrite And Multi-query Retrieval

**Learning point before coding:** query rewrite 是把用户问题、岗位、阶段、简历和上一轮回答扩展成多个检索 query，以提升召回覆盖。

**Planned files:**
- `backend_python/query_rewrite.py`
- `backend_python/retrieval_service.py`
- `tests/test_rag_query_rewrite.py`
- `docs/learning/19-query-rewrite和multi-query检索.md`

Deliverables:

```text
queryVariants
matchedQueryVariant
multi-query merge
```

---

## Task 5: Hybrid Weights And Rerank Explanation

**Learning point before coding:** hybrid search 不应该只有写死权重；rerank 不应该只是重排结果，还要解释 pre-rank、post-rank 和 rank change。

**Planned files:**
- `backend_python/retrieval_service.py`
- `backend_python/rag_logging.py`
- `tests/test_rag_hybrid_rerank_explain.py`
- `docs/learning/20-hybrid权重和rerank解释.md`

Deliverables:

```text
bm25Weight
vectorWeight
rankChange
rerankExplanation
```

---

## Task 6: Evaluation Case Management

**Learning point before coding:** RAG 质量不能只靠主观体验，需要维护 evaluation cases 并用 Hit@K、MRR、关键词覆盖率、metadataMatch 做回归。

**Planned files:**
- `backend_python/rag_evaluation.py`
- `backend_python/rag_evaluation_seed.py`
- `tests/test_rag_evaluation_management.py`
- `docs/learning/21-RAG评测case和质量指标.md`

Deliverables:

```text
evaluation case runner
quality metrics
case insight
```

---

## Task 7: Low-quality Recall Dashboard

**Learning point before coding:** 生产级 RAG 要能发现低质量召回，例如空召回、弱命中、metadata miss，而不是用户反馈问题后才排查。

**Planned files:**
- `backend_python/routes/admin.py`
- `backend_python/rag_quality.py`
- `app.js`
- `index.html`
- `styles.css`
- `tests/test_admin_rag_quality.py`
- `tests/frontend_admin_dashboard.test.mjs`
- `docs/learning/22-低质量召回日志和后台质量面板.md`

Deliverables:

```text
admin quality summary endpoint
low-quality recall list
frontend read-only panel
```

---

## Task 8: Vector Store Migration Abstraction

**Learning point before coding:** 当前可以继续用 SQLite 存 embedding_json，但要把向量库操作抽象出来，后续才容易迁移 Qdrant / pgvector。

**Planned files:**
- `backend_python/vector_store.py`
- `tests/test_vector_store_contract.py`
- `docs/learning/23-向量库持久化迁移设计.md`

Deliverables:

```text
VectorStore protocol
SQLiteVectorStore adapter
Qdrant/pgvector migration notes
```

---

## Verification Gates

After each completed task:

```powershell
python -m pytest <focused tests> -q
```

If frontend changes:

```powershell
node <focused frontend test>.mjs
```

Before claiming the goal complete:

```powershell
python -m pytest -q
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Also update:

```text
docs/pre-deployment-progress.md
docs/learning/<stage doc>.md
```
