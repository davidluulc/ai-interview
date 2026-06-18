# Production Hardening V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement Production Hardening V3.1 by making Celery worker mode observable and reliable for RAG ingestion while preserving eager-mode local tests and existing API compatibility.

**Architecture:** Keep SQLite as the local default and keep Celery eager mode as the default test path. Add a small reliability layer around Celery dispatch so HTTP routes can distinguish eager completion, queued worker-mode dispatch, and broker/dispatch failure. Surface the Celery mode and worker command through existing health/admin configuration responses and minimal Vue status labels.

**Tech Stack:** FastAPI, SQLAlchemy, Celery, pytest, Vue3, TypeScript, Vitest, PowerShell/Windows batch scripts.

---

## File Structure

- Modify: `backend_python/celery_app.py`
  - Add richer Celery status summary fields: mode, worker command, registered task names, broker configured flag.
- Modify: `backend_python/rag_ingestion_tasks.py`
  - Add dispatch result metadata, duration recording, and clearer eager vs queued behavior.
- Modify: `backend_python/routes/rag_documents.py`
  - Keep upload/retry API shape stable while relying on the improved dispatch helper.
- Create or modify: `scripts/start-celery-worker.cmd`
  - Provide a Windows-friendly worker startup command for real worker-mode rehearsal.
- Modify: `backend_python/routes/admin.py`
  - Ensure queued tasks are counted as in-progress and expose any new timing fields through existing serializers.
- Modify: `tests/test_celery_app.py`
  - Cover worker-mode status summary and task registration.
- Modify: `tests/test_rag_ingestion_celery.py`
  - Cover eager completion, simulated worker-mode queued dispatch, and dispatch failure.
- Modify: `tests/test_rag_documents_upload_route.py`
  - Cover upload/retry behavior in simulated non-eager worker mode.
- Modify: `tests/test_core_flows.py`
  - Cover `/api/health` Celery mode summary.
- Modify: `tests/test_admin_routes.py`
  - Cover `/api/admin/config` Celery mode summary.
- Modify: `frontend/src/api/admin.ts`
  - Add optional Celery mode fields without breaking existing types.
- Modify: `frontend/src/pages/app/AdminPage.vue`
  - Show minimal worker/eager wording in existing infrastructure panel.
- Modify: `frontend/src/pages/app/admin-page.test.ts`
  - Assert Celery mode wording is visible.
- Modify: `docs/project-baseline.md`
  - Record Production Hardening V3.1 completion when done.
- Modify: `docs/roadmap/current-state.md`
  - Mark V3.1 completed and leave V3.2/V3.3 pending.
- Modify: `docs/specs/README.md`, `docs/plans/README.md`
  - Update active/completed pointers after implementation.
- Move when complete: `docs/specs/active/production-hardening-v3-design.md`
  - To `docs/specs/completed/production-hardening-v3-design.md` only if this run intentionally closes the active V3 spec as V3.1 done and pending V3.2/V3.3 are documented.
- Move when complete: `docs/plans/active/production-hardening-v3.md`
  - To `docs/plans/completed/production-hardening-v3.md`.

---

## Task 1: Celery Mode Summary and Worker Startup Contract

**Files:**
- Modify: `tests/test_celery_app.py`
- Modify: `backend_python/celery_app.py`
- Create: `scripts/start-celery-worker.cmd`

- [x] **Step 1: Write failing Celery status tests**

Add tests to `tests/test_celery_app.py`:

```python
def test_celery_status_exposes_eager_mode_and_worker_command() -> None:
    status = build_celery_status(task_always_eager=True)

    assert status["status"] == "eager"
    assert status["mode"] == "eager"
    assert status["taskAlwaysEager"] is True
    assert status["workerRequired"] is False
    assert "celery" in status["workerCommand"]
    assert "backend_python.celery_app.celery_app" in status["workerCommand"]


def test_celery_status_exposes_worker_mode_when_not_eager() -> None:
    status = build_celery_status(
        broker_url="redis://localhost:6379/1",
        result_backend="redis://localhost:6379/2",
        task_always_eager=False,
    )

    assert status["status"] == "configured"
    assert status["mode"] == "worker"
    assert status["taskAlwaysEager"] is False
    assert status["workerRequired"] is True
    assert status["brokerConfigured"] is True
    assert "backend_python.tasks.rag_ingestion" in status["registeredTaskModules"]
```

- [x] **Step 2: Run focused RED test**

Run:

```powershell
python -m pytest tests/test_celery_app.py -q
```

Expected: fails because `mode`, `workerRequired`, `workerCommand`, `brokerConfigured`, and `registeredTaskModules` do not exist.

- [x] **Step 3: Implement status fields**

In `backend_python/celery_app.py`, define:

```python
CELERY_IMPORTS = (
    "backend_python.tasks.health",
    "backend_python.tasks.rag_evaluation",
    "backend_python.tasks.rag_ingestion",
)

CELERY_WORKER_COMMAND = "celery -A backend_python.celery_app.celery_app worker --loglevel=info --pool=solo"
```

Use `CELERY_IMPORTS` in `celery_app.conf.update(imports=CELERY_IMPORTS)`.

Update `build_celery_status()` to return:

```python
mode = "eager" if task_always_eager else "worker"
return {
    "status": "eager" if task_always_eager else "configured",
    "mode": mode,
    "taskAlwaysEager": bool(task_always_eager),
    "workerRequired": not bool(task_always_eager),
    "workerCommand": CELERY_WORKER_COMMAND,
    "brokerConfigured": bool(str(broker_url or "").strip()),
    "resultBackendConfigured": bool(str(result_backend or "").strip()),
    "brokerUrl": mask_database_url(broker_url),
    "resultBackend": mask_database_url(result_backend),
    "healthTask": "backend_python.tasks.health.ping_task",
    "registeredTaskModules": list(CELERY_IMPORTS),
}
```

- [x] **Step 4: Add worker startup script**

Create `scripts/start-celery-worker.cmd`:

```bat
@echo off
setlocal
cd /d "%~dp0\.."
echo Starting Celery worker for AI Interview System...
echo.
echo Required environment:
echo   CELERY_TASK_ALWAYS_EAGER=false
echo   CELERY_BROKER_URL=redis://localhost:6379/1
echo   CELERY_RESULT_BACKEND=redis://localhost:6379/2
echo.
celery -A backend_python.celery_app.celery_app worker --loglevel=info --pool=solo
endlocal
```

- [x] **Step 5: Run focused GREEN test**

Run:

```powershell
python -m pytest tests/test_celery_app.py -q
```

Expected: pass.

---

## Task 2: Dispatch Result Semantics for Eager, Queued, and Failure

**Files:**
- Modify: `tests/test_rag_ingestion_celery.py`
- Modify: `backend_python/rag_ingestion_tasks.py`

- [x] **Step 1: Write failing worker-mode dispatch test**

Add to `tests/test_rag_ingestion_celery.py`:

```python
def test_dispatch_rag_ingestion_task_keeps_task_queued_when_not_eager(monkeypatch) -> None:
    with SessionLocal() as db:
        user = create_test_user(db, "dispatch-queued@example.com")
        task = create_ingestion_task(
            db,
            user_id=user.id,
            title="Queued task",
            knowledge_base="role_knowledge",
            original_filename="queued.txt",
            visibility="private",
            metadata={},
        )
        merge_ingestion_task_input(db, task, {"textSnapshot": "Queued worker mode content."})

        from backend_python.tasks.rag_ingestion import run_rag_ingestion_task

        dispatched: list[str] = []

        class FakeAsyncResult:
            id = "celery-result-1"

        def fake_delay(task_id: str) -> FakeAsyncResult:
            dispatched.append(task_id)
            return FakeAsyncResult()

        monkeypatch.setattr(run_rag_ingestion_task, "delay", fake_delay)
        monkeypatch.setattr(run_rag_ingestion_task.app.conf, "task_always_eager", False)

        result = dispatch_rag_ingestion_task(db, task)

        assert dispatched == [task.task_id]
        assert result.status == "queued"
        serialized = serialize_ingestion_task(result)
        assert serialized["dispatchMode"] == "worker"
        assert serialized["celeryTaskId"] == "celery-result-1"
```

- [x] **Step 2: Write failing dispatch failure test**

Add:

```python
def test_dispatch_rag_ingestion_task_marks_failed_when_broker_dispatch_fails(monkeypatch) -> None:
    with SessionLocal() as db:
        user = create_test_user(db, "dispatch-failed@example.com")
        task = create_ingestion_task(
            db,
            user_id=user.id,
            title="Dispatch failure",
            knowledge_base="role_knowledge",
            original_filename="failure.txt",
            visibility="private",
            metadata={},
        )
        merge_ingestion_task_input(db, task, {"textSnapshot": "Retryable content."})

        from backend_python.tasks.rag_ingestion import run_rag_ingestion_task

        def fake_delay(task_id: str) -> None:
            raise RuntimeError("broker offline")

        monkeypatch.setattr(run_rag_ingestion_task, "delay", fake_delay)

        result = dispatch_rag_ingestion_task(db, task)

        assert result.status == "failed"
        assert result.can_retry == 1
        assert "Celery dispatch failed: broker offline" in result.error_message
        serialized = serialize_ingestion_task(result)
        assert serialized["dispatchMode"] == "failed"
```

- [x] **Step 3: Run focused RED tests**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_celery.py -q
```

Expected: fails because dispatch metadata is missing.

- [x] **Step 4: Implement dispatch metadata**

In `backend_python/rag_ingestion_tasks.py`:

- Add helper:

```python
def merge_ingestion_task_result(db: Session, task: RagIngestionTask, values: dict[str, Any]) -> RagIngestionTask:
    result_payload = json_loads(task.result_json)
    result_payload.update(values)
    task.result_json = json_dumps(result_payload)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
```

- Update `dispatch_rag_ingestion_task()`:

```python
def dispatch_rag_ingestion_task(db: Session, task: RagIngestionTask) -> RagIngestionTask:
    from .tasks.rag_ingestion import run_rag_ingestion_task

    queue_ingestion_task(db, task)
    try:
        async_result = run_rag_ingestion_task.delay(task.task_id)
        is_eager = bool(getattr(run_rag_ingestion_task.app.conf, "task_always_eager", False))
        db.refresh(task)
        if is_eager:
            return merge_ingestion_task_result(
                db,
                task,
                {
                    "dispatchMode": "eager",
                    "celeryTaskId": getattr(async_result, "id", ""),
                    "queuedAt": datetime.now(UTC).isoformat(),
                },
            )
        return merge_ingestion_task_result(
            db,
            task,
            {
                "dispatchMode": "worker",
                "celeryTaskId": getattr(async_result, "id", ""),
                "queuedAt": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as exc:
        task.can_retry = 1 if json_loads(task.input_json).get("textSnapshot") else 0
        merge_ingestion_task_result(db, task, {"dispatchMode": "failed"})
        fail_ingestion_task(db, task, error_message=f"Celery dispatch failed: {exc}")
    db.refresh(task)
    return task
```

- Update `serialize_ingestion_task()` to include:

```python
"dispatchMode": result.get("dispatchMode", ""),
"celeryTaskId": result.get("celeryTaskId", ""),
"queuedAt": result.get("queuedAt"),
"startedAt": result.get("startedAt"),
"durationMs": result.get("durationMs"),
```

- [x] **Step 5: Run focused GREEN tests**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_celery.py -q
```

Expected: pass.

---

## Task 3: Task Execution Timing and Failure Snapshot Reliability

**Files:**
- Modify: `tests/test_rag_ingestion_celery.py`
- Modify: `backend_python/rag_ingestion_tasks.py`

- [x] **Step 1: Write failing timing test**

Add:

```python
def test_execute_rag_ingestion_task_records_started_at_and_duration(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_test_user(db, "timed-ingestion@example.com")
        task = create_ingestion_task(
            db,
            user_id=user.id,
            title="Timed task",
            knowledge_base="role_knowledge",
            original_filename="timed.txt",
            visibility="private",
            metadata={},
        )
        merge_ingestion_task_input(db, task, {"textSnapshot": "Timed RAG ingestion content."})

    result = execute_rag_ingestion_task(task.task_id)

    assert result["status"] == "succeeded"
    assert result["startedAt"]
    assert isinstance(result["durationMs"], int)
    assert result["durationMs"] >= 0
```

- [x] **Step 2: Run focused RED test**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_celery.py::test_execute_rag_ingestion_task_records_started_at_and_duration -q
```

Expected: fails because `startedAt` and `durationMs` are missing.

- [x] **Step 3: Implement timing metadata**

In `execute_rag_ingestion_task()`:

- Before marking running:

```python
started_at = datetime.now(UTC)
```

- Merge `startedAt` into `result_json` before long work:

```python
merge_ingestion_task_result(db, task, {"startedAt": started_at.isoformat()})
```

- On success, include duration:

```python
duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
result = {
    "document": serialize_document(document),
    "preview": preview,
    **json_loads(task.result_json),
    "durationMs": duration_ms,
}
```

- On failure, call:

```python
merge_ingestion_task_result(
    db,
    task,
    {
        "startedAt": started_at.isoformat(),
        "durationMs": int((datetime.now(UTC) - started_at).total_seconds() * 1000),
        "failureStage": "execute",
    },
)
```

- [x] **Step 4: Run focused GREEN test**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_celery.py -q
```

Expected: pass.

---

## Task 4: Route Behavior in Simulated Worker Mode

**Files:**
- Modify: `tests/test_rag_documents_upload_route.py`
- Modify: `backend_python/routes/rag_documents.py` only if tests reveal route-specific bugs.

- [x] **Step 1: Write failing upload worker-mode route test**

Add:

```python
def test_upload_returns_queued_in_worker_mode(monkeypatch) -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_worker_mode")

    from backend_python.tasks.rag_ingestion import run_rag_ingestion_task

    class FakeAsyncResult:
        id = "worker-mode-upload"

    def fake_delay(task_id: str) -> FakeAsyncResult:
        return FakeAsyncResult()

    monkeypatch.setattr(run_rag_ingestion_task, "delay", fake_delay)
    monkeypatch.setattr(run_rag_ingestion_task.app.conf, "task_always_eager", False)

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "Worker mode", "knowledgeBase": "role_knowledge", "visibility": "private"},
        files={"file": ("worker.txt", b"Worker mode should return queued.", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["dispatchMode"] == "worker"
    assert body["document"] is None
```

- [x] **Step 2: Write retry worker-mode route test**

Add:

```python
def test_retry_returns_queued_in_worker_mode(monkeypatch) -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_retry_worker_mode")

    upload_response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "Retry worker", "knowledgeBase": "role_knowledge", "visibility": "private"},
        files={"file": ("retry-worker.txt", b"Retry worker mode content.", "text/plain")},
    )
    assert upload_response.status_code == 200
    task_id = upload_response.json()["taskId"]

    with SessionLocal() as db:
        task = db.scalar(select(RagIngestionTask).where(RagIngestionTask.task_id == task_id))
        assert task is not None
        task.status = "failed"
        task.error_message = "temporary failure"
        task.can_retry = 1
        db.add(task)
        db.commit()

    from backend_python.tasks.rag_ingestion import run_rag_ingestion_task

    class FakeAsyncResult:
        id = "worker-mode-retry"

    def fake_delay(task_id: str) -> FakeAsyncResult:
        return FakeAsyncResult()

    monkeypatch.setattr(run_rag_ingestion_task, "delay", fake_delay)
    monkeypatch.setattr(run_rag_ingestion_task.app.conf, "task_always_eager", False)

    retry_response = client.post(
        f"/api/rag/documents/ingestion-tasks/{task_id}/retry",
        headers=auth_headers(tokens),
    )

    assert retry_response.status_code == 200
    body = retry_response.json()
    assert body["status"] == "queued"
    assert body["retryCount"] == 1
    assert body["dispatchMode"] == "worker"
```

- [x] **Step 3: Run focused RED/GREEN tests**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py -q
```

Expected: pass after Task 2 implementation; if not, fix only route compatibility bugs.

---

## Task 5: Health/Admin Config and Minimal Frontend Wording

**Files:**
- Modify: `tests/test_core_flows.py`
- Modify: `tests/test_admin_routes.py`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [x] **Step 1: Add backend config tests**

In `tests/test_core_flows.py`, assert `/api/health` includes:

```python
assert body["infrastructure"]["celery"]["mode"] in {"eager", "worker"}
assert "workerCommand" in body["infrastructure"]["celery"]
```

In `tests/test_admin_routes.py::test_admin_config_returns_masked_infrastructure_status`, assert:

```python
assert body["infrastructure"]["celery"]["mode"] in {"eager", "worker"}
assert body["infrastructure"]["celery"]["workerCommand"]
```

- [x] **Step 2: Run backend focused tests**

Run:

```powershell
python -m pytest tests/test_core_flows.py::test_health_check tests/test_admin_routes.py::test_admin_config_returns_masked_infrastructure_status -q
```

Expected: pass after Task 1.

- [x] **Step 3: Add frontend type and display support**

In `frontend/src/api/admin.ts`, extend the Celery infrastructure interface with optional fields:

```ts
mode?: string;
workerRequired?: boolean;
workerCommand?: string;
brokerConfigured?: boolean;
resultBackendConfigured?: boolean;
registeredTaskModules?: string[];
```

In `frontend/src/pages/app/AdminPage.vue`, inside the existing Celery infrastructure display, add minimal text:

```vue
<small v-if="admin.config?.infrastructure?.celery?.mode">
  模式：{{ admin.config.infrastructure.celery.mode === "eager" ? "eager 本地测试" : "worker 异步模式" }}
</small>
<small v-if="admin.config?.infrastructure?.celery?.workerCommand">
  Worker：{{ admin.config.infrastructure.celery.workerCommand }}
</small>
```

- [x] **Step 4: Update frontend test**

In `frontend/src/pages/app/admin-page.test.ts`, update mocked config celery:

```ts
mode: "eager",
workerRequired: false,
workerCommand: "celery -A backend_python.celery_app.celery_app worker --loglevel=info --pool=solo",
brokerConfigured: true,
resultBackendConfigured: true,
registeredTaskModules: ["backend_python.tasks.rag_ingestion"]
```

Assert:

```ts
expect(wrapper.text()).toContain("模式：eager 本地测试");
expect(wrapper.text()).toContain("Worker：celery -A backend_python.celery_app.celery_app worker");
```

- [x] **Step 5: Run frontend focused test**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: pass.

---

## Task 6: Documentation Update and V3.1 Archival

**Files:**
- Modify: `docs/project-baseline.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Move: `docs/specs/active/production-hardening-v3-design.md`
- Move: `docs/plans/active/production-hardening-v3.md`

- [x] **Step 1: Update documentation**

Record:

```text
Production Hardening V3.1 已完成：Celery worker mode 可观测，RAG ingestion dispatch 能区分 eager 完成、worker queued 和 dispatch failed，并记录 dispatch/timing metadata。V3.2 安全与流量保护、V3.3 缓存/幂等/可观测性增强尚未执行。
```

- [x] **Step 2: Archive plan and spec**

Move:

```powershell
Move-Item -LiteralPath docs/specs/active/production-hardening-v3-design.md -Destination docs/specs/completed/production-hardening-v3-design.md
Move-Item -LiteralPath docs/plans/active/production-hardening-v3.md -Destination docs/plans/completed/production-hardening-v3.md
```

- [x] **Step 3: Update README pointers**

Set active spec and active plan to `暂无。`.

Set recent completed spec/plan to:

```text
docs/specs/completed/production-hardening-v3-design.md
docs/plans/completed/production-hardening-v3.md
```

Make clear only V3.1 is complete.

---

## Task 7: Full Verification and Browser Check

**Files:**
- No implementation files unless verification reveals a bug.

- [x] **Step 1: Backend full tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [x] **Step 2: Frontend full tests**

Run:

```powershell
cd frontend
npm.cmd run test
```

Expected: all tests pass.

- [x] **Step 3: Frontend build**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: build succeeds.

- [x] **Step 4: Browser verification**

Use the in-app browser to verify:

```text
http://127.0.0.1:5173/vue/app/knowledge
http://127.0.0.1:5173/vue/app/admin
```

Checks:

- Desktop has no visible `undefined`.
- Mobile has no visible `undefined`.
- Desktop has no horizontal overflow.
- Mobile has no horizontal overflow.
- Admin page shows Celery mode/worker wording without breaking existing infrastructure panel.
- Knowledge page still renders ingestion task status wording correctly.

- [x] **Step 5: Final diff review**

Run:

```powershell
git status --short
git diff --stat
```

Confirm:

- No Docker/Nginx/VPS changes.
- No RAG retrieval/rerank/evaluation algorithm rewrite.
- No Agent/LangGraph mainline rewrite.
- No OCR/Word/Excel/web parsing.

---

## Self-Review

Spec coverage:

- V3.1 worker command and mode switching: Task 1.
- Worker-mode queued behavior: Tasks 2 and 4.
- Dispatch failure handling: Task 2.
- Timing metadata: Task 3.
- Health/admin observability: Task 5.
- Minimal frontend wording: Task 5.
- Docs and archival: Task 6.
- Full verification/browser: Task 7.

Known deferred items:

- V3.2 token blacklist, rate limiting, and security hardening are documented in the spec but intentionally not implemented in this V3.1 plan.
- V3.3 caching, idempotency, and deeper observability are documented in the spec but intentionally not implemented in this V3.1 plan.

