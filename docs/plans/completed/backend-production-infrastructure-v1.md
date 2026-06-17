# Backend Production Infrastructure V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal, testable backend production infrastructure base for PostgreSQL compatibility, Redis health checks, Celery eager/health task support, and admin-visible infrastructure status while keeping SQLite as the local default.

**Architecture:** Add a small infrastructure summary layer instead of scattering production-service logic across routes. Keep PostgreSQL as configuration compatibility only, Redis as optional health/entrypoint only, and Celery as task infrastructure only. Expose the summarized state through existing health/admin endpoints and a minimal Vue3 admin display.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Redis client wrapper, Celery, Vue3, TypeScript, Vitest.

---

## File Structure

- Modify: `backend_python/database.py`
  - Extend database URL summary with masked URL, auto-init state, and migration path hints.
- Modify: `backend_python/redis_client.py`
  - Normalize Redis health to `disabled` / `ok` / `error`; keep Redis optional.
- Modify: `backend_python/celery_app.py`
  - Add Celery infrastructure summary helpers without dispatching worker-mode tasks.
- Modify: `backend_python/tasks/health.py`
  - Keep a JSON-serializable health task that can run in eager mode.
- Create: `backend_python/infrastructure.py`
  - Aggregate database, Redis, and Celery status for health/admin endpoints.
- Modify: `backend_python/routes/admin.py`
  - Return masked database URL and nested `infrastructure` summary from `/api/admin/config`.
- Modify: `backend_python/main.py`
  - Include infrastructure summary in `/api/health`.
- Modify: `tests/test_database_config.py`
  - Test masking, SQLite defaults, PostgreSQL compatibility summary.
- Modify: `tests/test_redis_client.py`
  - Test Redis disabled / ok / error including enabled-without-client.
- Modify: `tests/test_celery_app.py`
  - Test Celery summary and eager health task.
- Create: `tests/test_infrastructure_status.py`
  - Test combined infrastructure status does not leak passwords.
- Modify: `tests/test_admin_routes.py`
  - Test admin config contains database/redis/celery infrastructure status and masked URLs.
- Modify: `tests/test_core_flows.py`
  - Test `/api/health` includes infrastructure summary.
- Modify: `frontend/src/api/admin.ts`
  - Add infrastructure status types to `AdminConfig`.
- Modify: `frontend/src/pages/app/AdminPage.vue`
  - Minimal infrastructure cards under system config.
- Modify: `frontend/src/pages/app/admin-page.test.ts`
  - Assert infrastructure status renders without leaking passwords or `undefined`.
- Modify: `docs/project-baseline.md`
  - Record the completed backend production infrastructure base.
- Modify: `docs/roadmap/current-state.md`
  - Update current active/completed route.
- Modify: `docs/specs/README.md`
  - Move active spec pointer to none after completion.
- Modify: `docs/plans/README.md`
  - Move active plan pointer to none after completion.
- Move: `docs/specs/active/backend-production-infrastructure-v1-design.md` to `docs/specs/completed/backend-production-infrastructure-v1-design.md`
- Move: `docs/plans/active/backend-production-infrastructure-v1.md` to `docs/plans/completed/backend-production-infrastructure-v1.md`

---

### Task 1: Database Summary and URL Masking

**Files:**
- Modify: `tests/test_database_config.py`
- Modify: `backend_python/database.py`

- [ ] **Step 1: Write failing database summary tests**

Add tests that expect:

```python
def test_database_description_masks_password_and_marks_alembic_path() -> None:
    url = "postgresql+psycopg://app_user:secret@db:5432/interview"

    description = describe_database_url(url, auto_init=True)

    assert description["dialect"] == "postgresql+psycopg"
    assert description["isLocalSqlite"] is False
    assert description["usesExternalService"] is True
    assert description["autoInitEnabled"] is False
    assert description["migrationTool"] == "alembic"
    assert "secret" not in description["maskedUrl"]
    assert description["maskedUrl"] == "postgresql+psycopg://app_user:***@db:5432/interview"


def test_sqlite_database_description_keeps_local_path_visible() -> None:
    description = describe_database_url("sqlite:///data/app.db", auto_init=True)

    assert description["maskedUrl"] == "sqlite:///data/app.db"
    assert description["autoInitEnabled"] is True
    assert description["migrationTool"] == "metadata_create_all_for_local_sqlite"
```

- [ ] **Step 2: Run focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_database_config.py -q
```

Expected: fails because `describe_database_url()` does not accept `auto_init` and does not return the new fields.

- [ ] **Step 3: Implement minimal database summary**

Implement:

```python
def mask_database_url(database_url: str) -> str:
    ...

def describe_database_url(database_url: str, *, auto_init: bool = AUTO_INIT_DB) -> dict:
    ...
```

Rules:

- SQLite URLs remain visible.
- URLs with password replace password with `***`.
- Non-SQLite `autoInitEnabled` is always false.
- Non-SQLite `migrationTool` is `alembic`.

- [ ] **Step 4: Run focused test and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_database_config.py -q
```

Expected: pass.

---

### Task 2: Redis Health Three-State Contract

**Files:**
- Modify: `tests/test_redis_client.py`
- Modify: `backend_python/redis_client.py`

- [ ] **Step 1: Write failing Redis ok and unconfigured tests**

Add tests that expect:

```python
def test_build_redis_health_reports_ok_after_successful_ping() -> None:
    class HealthyClient:
        def ping(self) -> bool:
            return True

    health = build_redis_health(enabled=True, redis_url="redis://:secret@localhost:6379/0", client=HealthyClient())

    assert health.enabled is True
    assert health.status == "ok"
    assert health.url == "redis://:secret@localhost:6379/0"
    assert health.error == ""


def test_build_redis_health_enabled_without_client_is_error() -> None:
    health = build_redis_health(enabled=True, redis_url="redis://localhost:6379/0", client=None)

    assert health.enabled is True
    assert health.status == "error"
    assert "not configured" in health.error.lower()
```

- [ ] **Step 2: Run focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_redis_client.py -q
```

Expected: fails because enabled-without-client currently returns `unconfigured`.

- [ ] **Step 3: Implement minimal Redis health normalization**

Change enabled-without-client to `status="error"`. Do not make Redis required for local startup.

- [ ] **Step 4: Run focused test and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_redis_client.py -q
```

Expected: pass.

---

### Task 3: Celery Infrastructure Summary

**Files:**
- Modify: `tests/test_celery_app.py`
- Modify: `backend_python/celery_app.py`

- [ ] **Step 1: Write failing Celery summary test**

Add test:

```python
from backend_python.celery_app import build_celery_status


def test_build_celery_status_masks_urls_and_marks_eager_mode() -> None:
    status = build_celery_status(
        broker_url="redis://:broker-secret@localhost:6379/1",
        result_backend="redis://:result-secret@localhost:6379/2",
        task_always_eager=True,
    )

    assert status["status"] == "eager"
    assert status["taskAlwaysEager"] is True
    assert "broker-secret" not in status["brokerUrl"]
    assert "result-secret" not in status["resultBackend"]
    assert status["brokerUrl"] == "redis://:***@localhost:6379/1"
    assert status["resultBackend"] == "redis://:***@localhost:6379/2"
    assert status["healthTask"] == "backend_python.tasks.health.ping_task"
```

- [ ] **Step 2: Run focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_celery_app.py -q
```

Expected: fails because `build_celery_status` does not exist.

- [ ] **Step 3: Implement minimal Celery summary helper**

Implement helper in `backend_python/celery_app.py` using a reusable masking function or local URL masking helper.

Rules:

- Eager mode returns `status="eager"`.
- Worker/broker mode returns `status="configured"`.
- Do not dispatch `.delay()` in worker mode from the status helper.

- [ ] **Step 4: Run focused test and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_celery_app.py -q
```

Expected: pass.

---

### Task 4: Combined Infrastructure Status

**Files:**
- Create: `tests/test_infrastructure_status.py`
- Create: `backend_python/infrastructure.py`
- Modify: `backend_python/main.py`

- [ ] **Step 1: Write failing combined status tests**

Create tests:

```python
from backend_python.infrastructure import build_infrastructure_status


def test_build_infrastructure_status_combines_database_redis_and_celery() -> None:
    status = build_infrastructure_status(
        database_url="postgresql+psycopg://app:db-secret@db:5432/app",
        auto_init_db=True,
        redis_enabled=True,
        redis_url="redis://:redis-secret@redis:6379/0",
        redis_client=None,
        celery_broker_url="redis://:broker-secret@redis:6379/1",
        celery_result_backend="redis://:result-secret@redis:6379/2",
        celery_task_always_eager=False,
    )

    assert status["database"]["dialect"] == "postgresql+psycopg"
    assert status["database"]["autoInitEnabled"] is False
    assert status["redis"]["status"] == "error"
    assert status["celery"]["status"] == "configured"
    assert "db-secret" not in str(status)
    assert "redis-secret" not in str(status)
    assert "broker-secret" not in str(status)
    assert "result-secret" not in str(status)
```

- [ ] **Step 2: Run focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_infrastructure_status.py -q
```

Expected: fails because `backend_python.infrastructure` does not exist.

- [ ] **Step 3: Implement infrastructure aggregation**

Create `backend_python/infrastructure.py`:

```python
def mask_service_url(raw: str) -> str:
    ...

def build_infrastructure_status(...) -> dict[str, Any]:
    ...

def get_infrastructure_status() -> dict[str, Any]:
    ...
```

Use existing `describe_database_url`, `build_redis_health`, and `build_celery_status`.

- [ ] **Step 4: Add health endpoint infrastructure summary**

Modify `/api/health` to return:

```python
{
    "status": "ok",
    "service": "ai-mock-interview-system",
    "redis": get_redis_health(),
    "infrastructure": get_infrastructure_status(),
}
```

Keep the old top-level `redis` key for compatibility.

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_infrastructure_status.py tests/test_core_flows.py -q
```

Expected: pass.

---

### Task 5: Admin Config Observability

**Files:**
- Modify: `tests/test_admin_routes.py`
- Modify: `backend_python/routes/admin.py`

- [ ] **Step 1: Write failing admin config test**

Add a test that logs in as admin and asserts:

```python
response = client.get("/api/admin/config", headers=headers)
body = response.json()

assert body["databaseUrl"].startswith("sqlite:")
assert "infrastructure" in body
assert body["infrastructure"]["database"]["dialect"]
assert body["infrastructure"]["redis"]["status"] in {"disabled", "ok", "error"}
assert body["infrastructure"]["celery"]["status"] in {"eager", "configured"}
assert "password" not in str(body).lower()
```

- [ ] **Step 2: Run focused test and confirm RED**

Run:

```powershell
python -m pytest tests/test_admin_routes.py -q
```

Expected: fails because `infrastructure` is not returned yet.

- [ ] **Step 3: Implement admin config infrastructure response**

Modify `/api/admin/config` to return:

```python
{
    "modelName": QWEN_MODEL,
    "embeddingModel": DASHSCOPE_EMBEDDING_MODEL,
    "rerankModel": DASHSCOPE_RERANK_MODEL,
    "databaseUrl": describe_database_url(DATABASE_URL)["maskedUrl"],
    "infrastructure": get_infrastructure_status(),
}
```

- [ ] **Step 4: Run focused test and confirm GREEN**

Run:

```powershell
python -m pytest tests/test_admin_routes.py -q
```

Expected: pass.

---

### Task 6: Minimal Vue3 Admin Infrastructure Display

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Write failing frontend render test**

Update the mocked `adminStore.config` with:

```ts
infrastructure: {
  database: {
    dialect: "sqlite",
    isLocalSqlite: true,
    usesExternalService: false,
    autoInitEnabled: true,
    migrationTool: "metadata_create_all_for_local_sqlite",
    maskedUrl: "sqlite:///./data/app.db"
  },
  redis: {
    enabled: false,
    status: "disabled",
    url: "redis://localhost:6379/0",
    error: ""
  },
  celery: {
    status: "eager",
    taskAlwaysEager: true,
    brokerUrl: "redis://localhost:6379/1",
    resultBackend: "redis://localhost:6379/2",
    healthTask: "backend_python.tasks.health.ping_task"
  }
}
```

Add assertions:

```ts
expect(text).toContain("基础设施状态");
expect(text).toContain("SQLite 本地开发");
expect(text).toContain("Redis 未启用");
expect(text).toContain("Celery eager");
expect(text).not.toContain("undefined");
```

- [ ] **Step 2: Run focused frontend test and confirm RED**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: fails because UI does not render infrastructure status.

- [ ] **Step 3: Implement minimal types and UI**

Add infrastructure interfaces to `frontend/src/api/admin.ts`. In `AdminPage.vue`, add a small section inside system config that uses fallback text for missing values and never renders raw `undefined`.

- [ ] **Step 4: Run focused frontend test and confirm GREEN**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: pass.

---

### Task 7: Documentation Update and Archival

**Files:**
- Modify: `docs/project-baseline.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Move: `docs/specs/active/backend-production-infrastructure-v1-design.md`
- Move: `docs/plans/active/backend-production-infrastructure-v1.md`

- [ ] **Step 1: Update project baseline**

Record that Backend Production Infrastructure V1 added:

- database compatibility summary and URL masking;
- Redis optional health status;
- Celery eager/health task status;
- admin infrastructure observability;
- SQLite remains local default.

- [ ] **Step 2: Update current roadmap**

Mark Backend Production Infrastructure V1 as completed and set the next recommended phase to Async RAG Ingestion V2.

- [ ] **Step 3: Update specs/plans indexes**

Set active spec/plan to none and recent completed paths to:

```text
docs/specs/completed/backend-production-infrastructure-v1-design.md
docs/plans/completed/backend-production-infrastructure-v1.md
```

- [ ] **Step 4: Move active spec and plan to completed**

Use non-destructive file moves:

```powershell
Move-Item -LiteralPath docs/specs/active/backend-production-infrastructure-v1-design.md -Destination docs/specs/completed/backend-production-infrastructure-v1-design.md
Move-Item -LiteralPath docs/plans/active/backend-production-infrastructure-v1.md -Destination docs/plans/completed/backend-production-infrastructure-v1.md
```

---

### Task 8: Full Verification

**Files:**
- No implementation files unless verification reveals a bug.

- [ ] **Step 1: Run backend full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend full test suite**

Run:

```powershell
cd frontend
npm.cmd run test
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: build succeeds.

- [ ] **Step 4: Browser verification**

Start backend and frontend if needed, then verify:

- `http://127.0.0.1:5173/vue/app/admin` desktop layout renders infrastructure status.
- Mobile width around 390px has no horizontal overflow.
- Page text does not contain visible `undefined`.

- [ ] **Step 5: Final diff review**

Run:

```powershell
git status --short
git diff --stat
```

Check no unrelated files were changed.

