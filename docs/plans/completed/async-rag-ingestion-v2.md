# Async RAG Ingestion V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move RAG document ingestion execution from synchronous FastAPI route logic into a Celery task model while keeping local SQLite and Celery eager mode testable.

**Architecture:** FastAPI upload/retry endpoints create or update `RagIngestionTask`, store a minimal input snapshot, and dispatch a Celery task by `taskId`. A service function reads the task from the database, executes existing text extraction / preview / document creation logic, and writes task status back. Celery eager mode makes the same task run synchronously in tests without requiring Redis or a worker.

**Tech Stack:** FastAPI, SQLAlchemy, Celery, pytest, Vue3, TypeScript, Vitest.

---

## File Structure

- Create: `backend_python/tasks/rag_ingestion.py`
  - Celery task wrapper `run_rag_ingestion_task(task_id: str)`.
- Modify: `backend_python/celery_app.py`
  - Register `backend_python.tasks.rag_ingestion` in Celery imports.
- Modify: `backend_python/rag_ingestion_tasks.py`
  - Add `queued` status, dispatch helper, task lookup helpers, retry preparation, and `execute_rag_ingestion_task`.
- Modify: `backend_python/routes/rag_documents.py`
  - Upload/retry endpoints create task snapshots and dispatch Celery instead of doing long ingestion inline.
- Modify: `backend_python/routes/admin.py`
  - Count `queued` tasks as running/in-progress for admin summary.
- Modify: `tests/test_celery_app.py`
  - Assert RAG ingestion task is registered.
- Create: `tests/test_rag_ingestion_celery.py`
  - Cover eager task success/failure, DB task lookup, status writeback, and dispatch behavior.
- Modify: `tests/test_rag_documents_upload_route.py`
  - Update route expectations from synchronous `success` to `succeeded`/`queued` compatible task result.
- Modify: `tests/test_rag_ingestion_tasks.py`
  - Cover `queued` status and retry dispatch helpers.
- Modify: `frontend/src/api/knowledge.ts`
  - Allow `queued` task status.
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
  - Minimal async wording and status labels.
- Modify: `frontend/src/pages/app/knowledge-page.test.ts`
  - Assert queued/running states render clearly.
- Modify: `frontend/src/pages/app/AdminPage.vue`
  - Minimal queued status label support.
- Modify: `frontend/src/pages/app/admin-page.test.ts`
  - Assert admin ingestion monitor handles queued/running.
- Modify: `docs/project-baseline.md`
  - Record Async RAG Ingestion V2 after completion.
- Modify: `docs/roadmap/current-state.md`
  - Mark phase complete and set next recommendation.
- Modify: `docs/specs/README.md`, `docs/plans/README.md`
  - Clear active pointers and update recent completed references.
- Move: `docs/specs/active/async-rag-ingestion-v2-design.md` to `docs/specs/completed/async-rag-ingestion-v2-design.md`
- Move: `docs/plans/active/async-rag-ingestion-v2.md` to `docs/plans/completed/async-rag-ingestion-v2.md`

---

## Task 1: Celery Task Registration and Status Vocabulary

**Files:**
- Modify: `tests/test_celery_app.py`
- Modify: `tests/test_rag_ingestion_tasks.py`
- Modify: `backend_python/celery_app.py`
- Modify: `backend_python/rag_ingestion_tasks.py`

- [ ] **Step 1: Write failing tests**

Add tests that expect:

```python
assert "backend_python.tasks.rag_ingestion" in celery_app.conf.imports
```

and:

```python
task = create_ingestion_task(...)
update_ingestion_task(db, task, status="queued", progress=5, message="Queued.")
assert serialize_ingestion_task(task)["status"] == "queued"
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```powershell
python -m pytest tests/test_celery_app.py tests/test_rag_ingestion_tasks.py -q
```

Expected: fails because `queued` is invalid and task import is missing.

- [ ] **Step 3: Implement minimal vocabulary support**

Add `queued` to `VALID_TASK_STATUSES` and register `backend_python.tasks.rag_ingestion` in `celery_app.conf.imports`.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_celery_app.py tests/test_rag_ingestion_tasks.py -q
```

Expected: pass.

---

## Task 2: RAG Ingestion Execution Service

**Files:**
- Create: `tests/test_rag_ingestion_celery.py`
- Modify: `backend_python/rag_ingestion_tasks.py`

- [ ] **Step 1: Write failing service success test**

Create a test that:

- Creates a user and `RagIngestionTask`.
- Stores `textSnapshot`, metadata, title, visibility, and knowledgeBase in `input_json`.
- Calls `execute_rag_ingestion_task(task.task_id)`.
- Asserts task becomes `succeeded`, `progress=100`, `document_id` is set, and result contains a serialized document.

- [ ] **Step 2: Run focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_celery.py -q
```

Expected: fails because `execute_rag_ingestion_task` does not exist.

- [ ] **Step 3: Implement service**

Implement in `backend_python/rag_ingestion_tasks.py`:

```python
def get_ingestion_task_by_task_id(db: Session, task_id: str) -> RagIngestionTask | None:
    ...

def execute_rag_ingestion_task(task_id: str) -> dict[str, Any]:
    ...
```

Implementation rules:

- Open a fresh `SessionLocal`.
- Read task by `task_id`.
- Mark `running`.
- Read `textSnapshot`.
- Use existing `create_rag_document_with_embeddings`.
- On success call `succeed_ingestion_task`.
- On exception call `fail_ingestion_task`.
- Return `serialize_ingestion_task(task)`.

- [ ] **Step 4: Run focused test and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_celery.py -q
```

Expected: pass.

---

## Task 3: Celery Task Wrapper

**Files:**
- Create: `backend_python/tasks/rag_ingestion.py`
- Modify: `tests/test_rag_ingestion_celery.py`

- [ ] **Step 1: Write failing Celery eager task test**

Add a test that imports `run_rag_ingestion_task`, creates a task with `textSnapshot`, calls:

```python
result = run_rag_ingestion_task.delay(task.task_id).get(timeout=5)
```

and asserts `result["status"] == "succeeded"`.

- [ ] **Step 2: Run focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_celery.py -q
```

Expected: fails because `backend_python.tasks.rag_ingestion` does not exist.

- [ ] **Step 3: Implement Celery wrapper**

Create:

```python
from backend_python.celery_app import celery_app
from backend_python.rag_ingestion_tasks import execute_rag_ingestion_task

@celery_app.task(name="backend_python.tasks.rag_ingestion.run_rag_ingestion_task")
def run_rag_ingestion_task(task_id: str) -> dict:
    return execute_rag_ingestion_task(task_id)
```

- [ ] **Step 4: Run focused test and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_celery.py tests/test_celery_app.py -q
```

Expected: pass.

---

## Task 4: Dispatch Helper and Upload Route Migration

**Files:**
- Modify: `tests/test_rag_documents_upload_route.py`
- Modify: `backend_python/rag_ingestion_tasks.py`
- Modify: `backend_python/routes/rag_documents.py`

- [ ] **Step 1: Write failing upload route test**

Update upload route test to assert:

- Response has `taskId`.
- Response status is `succeeded` in eager mode.
- Persisted task status is `succeeded`.
- Task input snapshot contains `textSnapshot`.
- The route no longer returns legacy `"success"` status.

- [ ] **Step 2: Run focused route test and confirm RED**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py::test_upload_text_document_creates_rag_document -q
```

Expected: fails while route still returns legacy `"success"` and executes inline.

- [ ] **Step 3: Implement dispatch helper**

Add:

```python
def dispatch_rag_ingestion_task(db: Session, task: RagIngestionTask) -> RagIngestionTask:
    update_ingestion_task(db, task, status="queued", progress=max(task.progress, 5), message="RAG ingestion task queued.")
    from backend_python.tasks.rag_ingestion import run_rag_ingestion_task
    try:
        async_result = run_rag_ingestion_task.delay(task.task_id)
        if getattr(run_rag_ingestion_task.app.conf, "task_always_eager", False):
            db.refresh(task)
        return task
    except Exception as exc:
        task.can_retry = 1
        fail_ingestion_task(db, task, error_message=f"Celery dispatch failed: {exc}")
        return task
```

Refine implementation as needed to avoid stale sessions.

- [ ] **Step 4: Migrate upload route**

Route should:

- Validate knowledge base and metadata.
- Read file content.
- Extract and preview text in the request only as the minimum snapshot-building step.
- Store `textSnapshot` and `preview`.
- Dispatch Celery task.
- Return `serialize_ingestion_task(task)`.

This keeps large document creation out of route logic while preserving local eager completion.

- [ ] **Step 5: Run focused route tests and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py -q
```

Expected: pass after updating compatible assertions.

---

## Task 5: Retry Route Uses Celery Dispatch

**Files:**
- Modify: `tests/test_rag_documents_upload_route.py`
- Modify: `backend_python/routes/rag_documents.py`
- Modify: `backend_python/rag_ingestion_tasks.py`

- [ ] **Step 1: Write failing retry dispatch test**

Add or update a test to assert retry:

- Increments `retry_count`.
- Sets task to `queued` or final `succeeded` in eager mode.
- Produces a document via the Celery task path.
- Does not duplicate route-level document creation logic.

- [ ] **Step 2: Run focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py -q
```

Expected: fails while retry still creates document inline.

- [ ] **Step 3: Implement retry dispatch**

Retry route should:

- Fetch owned task.
- Check `can_retry_ingestion_task`.
- Increment `retry_count`.
- Reset `document_id` only if needed.
- Mark task `queued`.
- Call `dispatch_rag_ingestion_task`.
- Return `serialize_ingestion_task(task)`.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py tests/test_rag_ingestion_celery.py -q
```

Expected: pass.

---

## Task 6: Minimal Frontend Status Compatibility

**Files:**
- Modify: `frontend/src/api/knowledge.ts`
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
- Modify: `frontend/src/pages/app/knowledge-page.test.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write failing frontend tests**

Update tests to include `queued` ingestion tasks and assert:

- Knowledge page renders `queued` as “排队中”.
- Upload result with `queued` says task is created/queued, not “导入完成”.
- Admin ingestion monitor renders queued/running labels clearly.

- [ ] **Step 2: Run focused frontend tests and confirm RED**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/knowledge-page.test.ts src/pages/app/admin-page.test.ts
```

Expected: fails if queued labels are missing.

- [ ] **Step 3: Implement minimal labels**

Add status mappings:

```text
pending -> 待处理
queued -> 排队中
running -> 处理中
succeeded -> 已完成
success -> 已完成
failed -> 失败
```

Do not restructure pages.

- [ ] **Step 4: Run focused frontend tests and confirm GREEN**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/knowledge-page.test.ts src/pages/app/admin-page.test.ts
```

Expected: pass.

---

## Task 7: Documentation and Archival

**Files:**
- Modify: `docs/project-baseline.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Move: `docs/specs/active/async-rag-ingestion-v2-design.md`
- Move: `docs/plans/active/async-rag-ingestion-v2.md`

- [ ] **Step 1: Update docs**

Record:

- RAG ingestion is now Celery task based.
- Upload/retry dispatch by `taskId`.
- Eager mode keeps local tests simple.
- No Docker/Nginx/VPS/Qdrant/pgvector/OCR was introduced.

- [ ] **Step 2: Archive spec and plan**

Move:

```powershell
Move-Item -LiteralPath docs/specs/active/async-rag-ingestion-v2-design.md -Destination docs/specs/completed/async-rag-ingestion-v2-design.md
Move-Item -LiteralPath docs/plans/active/async-rag-ingestion-v2.md -Destination docs/plans/completed/async-rag-ingestion-v2.md
```

---

## Task 8: Full Verification and Browser Check

**Files:**
- No implementation files unless verification reveals a bug.

- [ ] **Step 1: Backend full tests**

Run:

```powershell
python -m pytest -q
```

- [ ] **Step 2: Frontend full tests**

Run:

```powershell
cd frontend
npm.cmd run test
```

- [ ] **Step 3: Frontend build**

Run:

```powershell
cd frontend
npm.cmd run build
```

- [ ] **Step 4: Browser verification**

Verify:

- `http://127.0.0.1:5173/vue/app/knowledge`
- `http://127.0.0.1:5173/vue/app/admin`

Checks:

- Desktop and mobile have no visible `undefined`.
- Desktop and mobile have no horizontal overflow.
- Knowledge page task status wording is not misleading.
- Admin ingestion monitor handles queued/running/succeeded/failed.

- [ ] **Step 5: Final diff review**

Run:

```powershell
git status --short
git diff --stat
```

Confirm changes stay inside the requested scope.

