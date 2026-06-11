# Backend Production V1 Postgres Redis Celery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a production-ready backend foundation with configurable database URLs, Redis infrastructure, Celery eager-testable tasks, and an async RAG evaluation task status model while keeping local SQLite development intact.

**Architecture:** Keep SQLite as the default local database and add pure configuration helpers around `DATABASE_URL` so tests can validate PostgreSQL/MySQL-style URLs without opening real network connections. Add Redis and Celery as optional infrastructure modules with disabled/eager modes for local testing, then expose a minimal task-status service and async RAG evaluation route without rewriting existing RAG internals.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, python-dotenv, optional redis-py, optional Celery, pytest, vanilla frontend `.mjs` tests.

---

## File Structure

- Modify `requirements.txt`: add `redis` and `celery`.
- Modify `.env.example`: document `DATABASE_URL`, Redis, and Celery settings.
- Modify `backend_python/config.py`: add Redis/Celery config values and boolean parsing helper.
- Modify `backend_python/database.py`: add explicit database config helpers while preserving existing `engine`, `SessionLocal`, and SQLite compatibility.
- Create `backend_python/redis_client.py`: optional Redis client, disabled fallback cache, health summary.
- Modify `backend_python/main.py`: add Redis health data to `/api/health`.
- Create `backend_python/celery_app.py`: Celery app factory/config with eager mode support.
- Create `backend_python/tasks/__init__.py`: task package marker.
- Create `backend_python/tasks/health.py`: `ping_task`.
- Create `backend_python/task_status.py`: in-memory/Redis-friendly task status service.
- Create `backend_python/tasks/rag_evaluation.py`: eager-testable RAG evaluation task wrapper.
- Modify `backend_python/routes/rag.py`: add async RAG evaluation submit/status endpoints without removing existing routes.
- Create tests:
  - `tests/test_database_config.py`
  - `tests/test_redis_client.py`
  - `tests/test_celery_app.py`
  - `tests/test_async_tasks.py`
- Create `docs/learning/11-PostgreSQL Redis Celery如何让后端走向生产化.md`.
- Modify progress docs and indexes:
  - `docs/roadmap/project-progress.md`
  - `docs/roadmap/current-state.md`
  - `docs/specs/README.md`
  - `docs/plans/README.md`

---

## Task 1: Database Configuration Tests and Helpers

**Files:**
- Modify: `backend_python/config.py`
- Modify: `backend_python/database.py`
- Modify: `.env.example`
- Create: `tests/test_database_config.py`

- [x] **Step 1: Write failing database configuration tests**

Create `tests/test_database_config.py` with tests for:

```python
from backend_python.database import build_connect_args, build_engine_options, describe_database_url


def test_sqlite_database_url_uses_check_same_thread_false():
    assert build_connect_args("sqlite:///data/app.db") == {"check_same_thread": False}
    description = describe_database_url("sqlite:///data/app.db")
    assert description["dialect"] == "sqlite"
    assert description["isLocalSqlite"] is True


def test_postgresql_database_url_does_not_use_sqlite_connect_args():
    assert build_connect_args("postgresql+psycopg://user:pass@localhost:5432/app") == {}
    options = build_engine_options("postgresql+psycopg://user:pass@localhost:5432/app")
    assert options["connect_args"] == {}
    assert options["pool_pre_ping"] is True
    description = describe_database_url("postgresql+psycopg://user:pass@localhost:5432/app")
    assert description["dialect"] == "postgresql+psycopg"
    assert description["isLocalSqlite"] is False
```

- [x] **Step 2: Run red test**

Run:

```powershell
python -m pytest tests/test_database_config.py -q
```

Expected: fail because helper functions do not exist.

- [x] **Step 3: Implement database helpers**

Update `backend_python/database.py`:

```python
def build_connect_args(database_url: str) -> dict:
    return {"check_same_thread": False} if str(database_url).startswith("sqlite") else {}


def build_engine_options(database_url: str) -> dict:
    options = {"connect_args": build_connect_args(database_url)}
    if not str(database_url).startswith("sqlite"):
        options["pool_pre_ping"] = True
    return options


def describe_database_url(database_url: str) -> dict:
    raw = str(database_url or "")
    dialect = raw.split(":", 1)[0] if ":" in raw else raw
    return {
        "dialect": dialect,
        "isLocalSqlite": raw.startswith("sqlite"),
        "usesExternalService": not raw.startswith("sqlite"),
    }
```

Update engine creation to use `create_engine(DATABASE_URL, **build_engine_options(DATABASE_URL))`.

- [x] **Step 4: Update `.env.example`**

Add:

```env
# Local default keeps development simple.
DATABASE_URL=sqlite:///data/app.db

# PostgreSQL example for deployment; not required for local development.
# DATABASE_URL=postgresql+psycopg://ai_interview:your_password@127.0.0.1:5432/ai_interview

# MySQL is useful for learning, but PostgreSQL remains the recommended production target for this project.
# DATABASE_URL=mysql+pymysql://ai_interview:your_password@127.0.0.1:3306/ai_interview
```

- [x] **Step 5: Run green test**

Run:

```powershell
python -m pytest tests/test_database_config.py tests/test_database_migrations.py -q
```

Expected: pass.

---

## Task 2: Redis Infrastructure Layer

**Files:**
- Modify: `backend_python/config.py`
- Create: `backend_python/redis_client.py`
- Modify: `backend_python/main.py`
- Modify: `.env.example`
- Create: `tests/test_redis_client.py`
- Modify: `tests/test_core_flows.py`

- [x] **Step 1: Write failing Redis client tests**

Create `tests/test_redis_client.py` with:

```python
from backend_python.redis_client import DisabledRedisCache, RedisHealth, build_redis_health


def test_disabled_redis_cache_is_safe_noop():
    cache = DisabledRedisCache()
    assert cache.enabled is False
    assert cache.get("missing") is None
    assert cache.set("key", "value", ex=60) is False
    assert cache.exists("key") is False
    assert cache.delete("key") is False


def test_build_redis_health_disabled():
    health = build_redis_health(enabled=False, redis_url="redis://localhost:6379/0", client=None)
    assert isinstance(health, RedisHealth)
    assert health.status == "disabled"
    assert health.enabled is False
```

- [x] **Step 2: Write failing health route test**

Update `tests/test_core_flows.py` so `/api/health` returns a `redis` object with `enabled` and `status`.

- [x] **Step 3: Run red tests**

Run:

```powershell
python -m pytest tests/test_redis_client.py tests/test_core_flows.py -q
```

Expected: fail because Redis module and health response do not exist.

- [x] **Step 4: Add Redis config and optional client**

Update `backend_python/config.py`:

```python
def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


REDIS_ENABLED = env_bool("REDIS_ENABLED", False)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

Create `backend_python/redis_client.py`:

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class RedisHealth:
    enabled: bool
    status: str
    url: str
    error: str = ""


class DisabledRedisCache:
    enabled = False

    def get(self, key: str) -> None:
        return None

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        return False

    def delete(self, key: str) -> bool:
        return False

    def exists(self, key: str) -> bool:
        return False


def build_redis_health(*, enabled: bool, redis_url: str, client: Any | None) -> RedisHealth:
    if not enabled:
        return RedisHealth(enabled=False, status="disabled", url=redis_url)
    try:
        if client is None:
            return RedisHealth(enabled=True, status="unconfigured", url=redis_url, error="Redis client is not configured.")
        client.ping()
        return RedisHealth(enabled=True, status="ok", url=redis_url)
    except Exception as exc:
        return RedisHealth(enabled=True, status="error", url=redis_url, error=str(exc))
```

Use optional import for `redis` so tests can run even before dependency installation edge cases.

- [x] **Step 5: Update `/api/health`**

Return:

```python
{
    "status": "ok",
    "service": "ai-mock-interview-system",
    "redis": build_redis_health(...).__dict__,
}
```

Update existing health test to keep checking `status == "ok"`.

- [x] **Step 6: Update `.env.example`**

Add:

```env
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379/0
```

- [x] **Step 7: Run green tests**

Run:

```powershell
python -m pytest tests/test_redis_client.py tests/test_core_flows.py -q
```

Expected: pass.

---

## Task 3: Celery App and Health Task

**Files:**
- Modify: `requirements.txt`
- Modify: `backend_python/config.py`
- Create: `backend_python/celery_app.py`
- Create: `backend_python/tasks/__init__.py`
- Create: `backend_python/tasks/health.py`
- Modify: `.env.example`
- Create: `tests/test_celery_app.py`

- [x] **Step 1: Write failing Celery tests**

Create `tests/test_celery_app.py`:

```python
from backend_python.celery_app import celery_app
from backend_python.tasks.health import ping_task


def test_celery_app_uses_eager_mode_for_tests():
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True


def test_ping_task_returns_json_serializable_payload():
    result = ping_task.delay().get(timeout=5)
    assert result["status"] == "ok"
    assert result["task"] == "ping"
```

- [x] **Step 2: Run red test**

Run:

```powershell
python -m pytest tests/test_celery_app.py -q
```

Expected: fail because Celery module does not exist.

- [x] **Step 3: Add dependencies**

Update `requirements.txt`:

```text
redis==5.2.1
celery==5.4.0
```

- [x] **Step 4: Add Celery config**

Update `backend_python/config.py`:

```python
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)
```

Create `backend_python/celery_app.py` with a Celery app configured for eager mode in tests/local default.

Create `backend_python/tasks/health.py`:

```python
from backend_python.celery_app import celery_app


@celery_app.task(name="backend_python.tasks.health.ping_task")
def ping_task() -> dict:
    return {"status": "ok", "task": "ping"}
```

- [x] **Step 5: Update `.env.example`**

Add:

```env
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_ALWAYS_EAGER=true
```

- [x] **Step 6: Run green tests**

Run:

```powershell
python -m pytest tests/test_celery_app.py -q
```

Expected: pass.

---

## Task 4: Async Task Status Service and RAG Evaluation Task

**Files:**
- Create: `backend_python/task_status.py`
- Create: `backend_python/tasks/rag_evaluation.py`
- Modify: `backend_python/routes/rag.py`
- Create: `tests/test_async_tasks.py`

- [x] **Step 1: Write failing task status tests**

Create `tests/test_async_tasks.py`:

```python
from backend_python.task_status import create_task_status, fail_task_status, get_task_status, succeed_task_status


def test_task_status_lifecycle():
    task = create_task_status(task_type="rag_evaluation")
    assert task["status"] == "pending"
    assert task["taskType"] == "rag_evaluation"

    succeed_task_status(task["taskId"], result={"caseCount": 1})
    done = get_task_status(task["taskId"])
    assert done["status"] == "success"
    assert done["progress"] == 100
    assert done["result"] == {"caseCount": 1}


def test_task_status_records_failure():
    task = create_task_status(task_type="rag_evaluation")
    fail_task_status(task["taskId"], error="boom")
    failed = get_task_status(task["taskId"])
    assert failed["status"] == "failed"
    assert failed["error"] == "boom"
```

- [x] **Step 2: Write failing RAG async route test**

Add a test in `tests/test_async_tasks.py` using `TestClient(app)`:
- `POST /api/rag/evaluation/tasks` returns `taskId` and `status`.
- `GET /api/rag/evaluation/tasks/{task_id}` returns the same task status.

- [x] **Step 3: Run red test**

Run:

```powershell
python -m pytest tests/test_async_tasks.py -q
```

Expected: fail because task status service/routes do not exist.

- [x] **Step 4: Implement task status service**

Create `backend_python/task_status.py` with an in-memory store:

```python
from datetime import datetime, timezone
from uuid import uuid4

_TASKS: dict[str, dict] = {}

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```

Implement `create_task_status`, `get_task_status`, `succeed_task_status`, `fail_task_status`.

- [x] **Step 5: Implement RAG evaluation task**

Create `backend_python/tasks/rag_evaluation.py` with a Celery task that returns a small JSON-serializable result and updates task status in eager mode.

- [x] **Step 6: Add routes**

Modify `backend_python/routes/rag.py`:

```text
POST /api/rag/evaluation/tasks
GET /api/rag/evaluation/tasks/{task_id}
```

Keep existing `/api/rag/debug` and log routes unchanged.

- [x] **Step 7: Run green tests**

Run:

```powershell
python -m pytest tests/test_async_tasks.py tests/test_rag_evaluation_management.py -q
```

Expected: pass.

---

## Task 5: Learning Docs and Roadmap Updates

**Files:**
- Create: `docs/learning/11-PostgreSQL Redis Celery如何让后端走向生产化.md`
- Modify: `docs/roadmap/project-progress.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [x] **Step 1: Write Chinese learning doc**

Include:
- SQLite / MySQL / PostgreSQL differences.
- Why local default remains SQLite.
- What Redis does in backend systems.
- What Celery does for AI/RAG long-running jobs.
- Difference between sync HTTP requests and async tasks.
- How Docker/Nginx/cloud deployment will later connect these pieces.
- Interview explanation.

- [x] **Step 2: Update roadmap progress**

Record completed modules:
- database config helpers.
- Redis disabled fallback and health.
- Celery eager task.
- async RAG evaluation task status.

- [x] **Step 3: Update active/completed docs**

Only after tests pass:
- move active spec to `docs/specs/completed/backend-production-v1-postgres-redis-celery-design.md`.
- move active plan to `docs/plans/completed/backend-production-v1-postgres-redis-celery.md`.
- update README files so active dirs are empty.

- [x] **Step 4: Verify docs**

Run:

```powershell
rg -n "后端生产化 V1|Redis|Celery|DATABASE_URL" docs/learning docs/roadmap docs/specs/README.md docs/plans/README.md
```

Expected: relevant completed-stage entries appear.

---

## Task 6: Full Verification and Browser Smoke Check

**Files:**
- No new files.

- [x] **Step 1: Run backend suite**

Run:

```powershell
python -m pytest -q
```

Expected: all backend tests pass.

- [x] **Step 2: Run frontend tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected: all frontend tests pass.

- [x] **Step 3: Browser smoke check**

Use the in-app browser for `http://127.0.0.1:8000/` if server is running:
- page loads.
- no `undefined` text.
- console has no error.

If no server is running, use `Invoke-WebRequest` to confirm whether the local service is unavailable, and report that browser validation could not run because the dev server was not active.

---

## Completion Notes

Do not mark this stage complete until:
- plan exists and has been executed.
- local SQLite default still works.
- database URL helpers have tests.
- Redis disabled fallback and health have tests.
- Celery eager ping task has tests.
- async RAG evaluation task status has tests.
- learning and roadmap docs are updated.
- active spec and plan are moved to completed after verification.
- backend and frontend full test suites pass.

