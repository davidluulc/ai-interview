# Pre-Launch Delivery Roadmap V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the AI interview system from a feature-complete local project toward a deployable, explainable, resume-ready project by tightening async worker readiness, PostgreSQL compatibility, deployment integration, and project storytelling materials.

**Architecture:** Keep local development lightweight with SQLite and eager/fallback execution while making production paths explicit and testable. The plan adds worker readiness summaries, PostgreSQL compatibility checks, deployment validation, and final explanation/resume artifacts without rewriting completed RAG, Agent, LangGraph, Vue3, or hardening work.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, PostgreSQL-compatible configuration, Redis, Celery, Vue3, Vite, TypeScript, Docker Compose, Nginx, pytest, Vitest.

---

## Current Stage Guardrails

- Active spec: `docs/specs/active/pre-launch-delivery-roadmap-v4-design.md`.
- Active plan: `docs/plans/active/pre-launch-delivery-roadmap-v4.md`.
- Do not repeat completed stages:
  - Backend Production Infrastructure V1.
  - Async RAG Ingestion V2.
  - Production Hardening V3.1.
  - Production Hardening V3.2 + V3.3.
- Keep SQLite as the default local database.
- Do not require PostgreSQL for every local test run.
- Do not add Qdrant, pgvector, object storage, Kubernetes, Prometheus, Grafana, Flower, OCR, Word/Excel/web parsing, or a full RBAC admin system in this roadmap.
- Every code task must follow TDD: write or update tests first, verify the test fails for the expected reason, implement the minimal code, then verify the test passes.

---

## File Responsibility Map

### Async Worker Readiness V4

- Modify: `backend_python/celery_app.py`
  - Extend Celery status with worker readiness fields that are safe to expose in admin/config.
- Modify: `backend_python/rag_ingestion_tasks.py`
  - Add small serialization helpers for worker readiness and task lifecycle summaries if needed.
- Modify: `backend_python/routes/admin.py`
  - Include async worker readiness in admin ingestion/config payloads.
- Modify: `backend_python/infrastructure.py`
  - Aggregate Celery/Redis worker readiness without requiring real Redis in tests.
- Modify: `frontend/src/api/admin.ts`
  - Type or pass through new admin worker readiness fields.
- Modify: `frontend/src/pages/app/AdminPage.vue`
  - Display worker readiness and ingestion task lifecycle summary in plain product language.
- Test: `tests/test_celery_app.py`
  - Cover eager, worker, broker missing, and masked URL readiness cases.
- Test: `tests/test_admin_routes.py`
  - Cover admin config or ingestion endpoint exposes worker readiness without secrets.
- Test: `frontend/src/pages/app/admin-page.test.ts`
  - Cover worker readiness summary rendering.
- Docs: `docs/deployment/celery-worker-readiness.md`
  - Explain local eager, fallback, worker mode, and Windows worker startup.

### PostgreSQL Compatibility V4

- Modify: `backend_python/database.py`
  - Ensure database description, URL masking, and engine config remain SQLite/PostgreSQL compatible.
- Modify: `.env.example`
  - Keep SQLite default and add clear PostgreSQL optional example.
- Modify: `.env.production.example`
  - Ensure production PostgreSQL, Redis, and Celery variables are explicit and safe.
- Modify: `docker-compose.yml`
  - Validate app/worker/db/redis/nginx variable alignment and avoid duplicated drift where possible.
- Test: `tests/test_database_config.py`
  - Cover PostgreSQL URL recognition and masked output.
- Test: `tests/test_deployment_config.py`
  - Cover compose/environment assumptions relevant to PostgreSQL.
- Docs: `docs/deployment/postgresql-compatibility-v4.md`
  - Explain local SQLite default, optional Docker PostgreSQL, and production switch.

### Deployment Integration V4

- Modify: `Dockerfile`
  - Keep image compatible with app and worker runtime.
- Modify: `docker-compose.yml`
  - Ensure FastAPI, PostgreSQL, Redis, Celery worker, and Nginx can be reasoned about as one deployment graph.
- Modify: `deploy/nginx/ai-interview.conf`
  - Verify Vue/static/API proxy assumptions are documented and testable.
- Modify: `tests/test_deployment_config.py`
  - Add config-level checks for compose services, worker command, Nginx mount, and required env vars.
- Docs: `docs/deployment/pre-launch-deployment-runbook-v4.md`
  - Add step-by-step runbook for VPS/domain/Cloudflare/HTTPS without storing real secrets.
- Docs: `docs/deployment/pre-launch-checklist-v4.md`
  - Add final launch checklist and rollback notes.

### Project Explanation & Resume Pack V1

- Create: `docs/project-explanation/ai-interview-system-overview.md`
  - Full project narrative: business background, user flow, system architecture, RAG, Agent/LangGraph, training loop, observability, productionization, trade-offs.
- Create: `docs/project-explanation/interview-deep-dive-qa.md`
  - Interview Q&A bank for likely deep dives.
- Create: `docs/project-explanation/resume-bullets-python-backend.md`
  - Resume material tuned for Python backend internships.
- Create: `docs/project-explanation/resume-bullets-ai-application.md`
  - Resume material tuned for AI application development internships.
- Create: `docs/project-explanation/project-demo-script.md`
  - A demo script for showing the project from login to interview to admin observability.

### Roadmap And Status

- Modify: `docs/roadmap/current-state.md`
  - Update current phase after each completed sub-stage.
- Modify: `docs/specs/README.md`
  - Keep active/completed status accurate.
- Modify: `docs/plans/README.md`
  - Keep active/completed status accurate.

---

## Phase A: Async Worker Readiness V4

### Task A1: Add Celery Worker Readiness Status

**Files:**
- Modify: `backend_python/celery_app.py`
- Test: `tests/test_celery_app.py`

- [x] **Step 1: Write the failing tests**

Append these tests to `tests/test_celery_app.py`:

```python
def test_celery_status_exposes_worker_readiness_when_eager() -> None:
    status = build_celery_status(
        broker_url="redis://localhost:6379/1",
        result_backend="redis://localhost:6379/2",
        task_always_eager=True,
    )

    assert status["workerReadiness"]["mode"] == "eager"
    assert status["workerReadiness"]["readyForWorker"] is False
    assert status["workerReadiness"]["requiresExternalWorker"] is False
    assert "当前为 eager/test 模式" in status["workerReadiness"]["message"]
    assert status["workerReadiness"]["missingRequirements"] == []


def test_celery_status_exposes_worker_readiness_when_worker_configured() -> None:
    status = build_celery_status(
        broker_url="redis://localhost:6379/1",
        result_backend="redis://localhost:6379/2",
        task_always_eager=False,
    )

    assert status["workerReadiness"]["mode"] == "worker"
    assert status["workerReadiness"]["readyForWorker"] is True
    assert status["workerReadiness"]["requiresExternalWorker"] is True
    assert status["workerReadiness"]["missingRequirements"] == []
    assert "Celery worker" in status["workerReadiness"]["message"]


def test_celery_status_exposes_missing_worker_requirements() -> None:
    status = build_celery_status(
        broker_url="",
        result_backend="",
        task_always_eager=False,
    )

    assert status["workerReadiness"]["mode"] == "worker"
    assert status["workerReadiness"]["readyForWorker"] is False
    assert "broker_url" in status["workerReadiness"]["missingRequirements"]
    assert "result_backend" in status["workerReadiness"]["missingRequirements"]
```

- [x] **Step 2: Run the tests and verify RED**

Run:

```powershell
python -m pytest tests/test_celery_app.py -q
```

Expected: FAIL with `KeyError: 'workerReadiness'`.

- [x] **Step 3: Implement minimal worker readiness helper**

In `backend_python/celery_app.py`, add this helper above `build_celery_status`:

```python
def build_worker_readiness(
    *,
    broker_url: str,
    result_backend: str,
    task_always_eager: bool,
) -> dict:
    missing = []
    if not str(broker_url or "").strip():
        missing.append("broker_url")
    if not str(result_backend or "").strip():
        missing.append("result_backend")

    if task_always_eager:
        return {
            "mode": "eager",
            "readyForWorker": False,
            "requiresExternalWorker": False,
            "missingRequirements": [],
            "message": "当前为 eager/test 模式，任务会在请求进程内同步执行，不需要外部 Celery worker。",
        }

    ready = not missing
    return {
        "mode": "worker",
        "readyForWorker": ready,
        "requiresExternalWorker": True,
        "missingRequirements": missing,
        "message": (
            "Celery worker 模式已具备 broker/result backend 配置，需要单独启动 Celery worker。"
            if ready
            else "Celery worker 模式缺少必要配置，任务无法稳定进入外部队列。"
        ),
    }
```

Then add this key to the dictionary returned by `build_celery_status`:

```python
"workerReadiness": build_worker_readiness(
    broker_url=broker_url,
    result_backend=result_backend,
    task_always_eager=task_always_eager,
),
```

- [x] **Step 4: Run the tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_celery_app.py -q
```

Expected: all tests in `tests/test_celery_app.py` pass.

- [x] **Step 5: Commit Task A1**

```powershell
git add backend_python/celery_app.py tests/test_celery_app.py
git commit -m "feat: expose celery worker readiness"
```

### Task A2: Expose Worker Readiness Through Admin Config

**Files:**
- Modify: `tests/test_admin_routes.py`
- Modify: `backend_python/routes/admin.py` only if existing `/api/admin/config` does not already expose the new nested field through infrastructure.

- [x] **Step 1: Write the failing test**

Extend `test_admin_config_returns_masked_infrastructure_status` in `tests/test_admin_routes.py` with:

```python
    assert "workerReadiness" in body["infrastructure"]["celery"]
    assert body["infrastructure"]["celery"]["workerReadiness"]["mode"] in {"eager", "worker"}
    assert isinstance(body["infrastructure"]["celery"]["workerReadiness"]["missingRequirements"], list)
    assert "secret" not in str(body["infrastructure"]["celery"]["workerReadiness"]).lower()
```

- [x] **Step 2: Run the test and verify RED or already covered**

Run:

```powershell
python -m pytest tests/test_admin_routes.py::test_admin_config_returns_masked_infrastructure_status -q
```

Expected if Task A1 has not been implemented: FAIL with missing `workerReadiness`.
Expected if Task A1 is already implemented and `/api/admin/config` passes through infrastructure: PASS.

- [x] **Step 3: Implement only if needed**

If the test fails after Task A1, inspect `backend_python/routes/admin.py` and ensure `admin_config()` returns:

```python
"infrastructure": get_infrastructure_status(),
```

If it already does, do not change production code.

- [x] **Step 4: Run the focused admin test**

Run:

```powershell
python -m pytest tests/test_admin_routes.py::test_admin_config_returns_masked_infrastructure_status -q
```

Expected: PASS.

- [x] **Step 5: Commit Task A2**

```powershell
git add tests/test_admin_routes.py backend_python/routes/admin.py
git commit -m "test: cover admin worker readiness summary"
```

### Task A3: Render Worker Readiness In Vue Admin Page

**Files:**
- Modify: `frontend/src/pages/app/admin-page.test.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/api/admin.ts` if types need updating.

- [x] **Step 1: Write the failing frontend test**

In `frontend/src/pages/app/admin-page.test.ts`, add a test that mounts the admin page with config containing:

```typescript
infrastructure: {
  database: { dialect: 'sqlite', maskedUrl: 'sqlite:///./local.db' },
  redis: { status: 'disabled', url: '' },
  celery: {
    status: 'configured',
    mode: 'worker',
    taskAlwaysEager: false,
    workerCommand: 'celery -A backend_python.celery_app.celery_app worker --loglevel=info --pool=solo',
    workerReadiness: {
      mode: 'worker',
      readyForWorker: true,
      requiresExternalWorker: true,
      missingRequirements: [],
      message: 'Celery worker 模式已具备 broker/result backend 配置，需要单独启动 Celery worker。',
    },
  },
}
```

Assert that the rendered page includes:

```typescript
expect(screen.getByText(/异步任务 Worker/)).toBeTruthy()
expect(screen.getByText(/需要单独启动 Celery worker/)).toBeTruthy()
```

- [x] **Step 2: Run the frontend test and verify RED**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: FAIL because the UI does not render the new worker readiness text yet.

- [x] **Step 3: Implement minimal UI rendering**

In `frontend/src/pages/app/AdminPage.vue`, in the infrastructure/system config section, add a compact worker readiness row:

```vue
<div v-if="admin.config?.infrastructure?.celery?.workerReadiness" class="admin-config-row">
  <span>异步任务 Worker</span>
  <strong>{{ admin.config.infrastructure.celery.workerReadiness.message }}</strong>
</div>
```

If TypeScript complains, update `frontend/src/api/admin.ts` interfaces to include:

```typescript
workerReadiness?: {
  mode: string
  readyForWorker: boolean
  requiresExternalWorker: boolean
  missingRequirements: string[]
  message: string
}
```

- [x] **Step 4: Run the frontend test and verify GREEN**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: PASS.

- [x] **Step 5: Commit Task A3**

```powershell
git add frontend/src/pages/app/admin-page.test.ts frontend/src/pages/app/AdminPage.vue frontend/src/api/admin.ts
git commit -m "feat: show async worker readiness in admin"
```

### Task A4: Document Async Worker Operating Modes

**Files:**
- Create: `docs/deployment/celery-worker-readiness.md`
- Modify: `docs/roadmap/current-state.md`

- [x] **Step 1: Create worker readiness docs**

Create `docs/deployment/celery-worker-readiness.md` with:

```markdown
# Celery Worker Readiness：RAG 异步任务运行说明

## 为什么需要 Worker

RAG 文档上传、文本解析、清洗、切 chunk 和入库是慢任务。HTTP 接口应该快速返回 taskId，后台 Celery worker 继续处理任务，前端和管理员后台通过任务状态观察进度。

## 三种运行模式

### local/eager

用于本地开发和自动化测试。`CELERY_TASK_ALWAYS_EAGER=true` 时任务在当前进程内同步执行，不需要 Redis 或外部 worker。

### fallback

Redis 或 Celery 不可用时，系统应返回可解释的失败或降级状态，不暴露密钥，不让任务静默丢失。

### worker

用于生产或部署演练。`CELERY_TASK_ALWAYS_EAGER=false`，FastAPI 把任务派发到 Redis broker，Celery worker 从队列消费并执行。

## Windows 本地启动示例

```powershell
set CELERY_TASK_ALWAYS_EAGER=false
set CELERY_BROKER_URL=redis://localhost:6379/1
set CELERY_RESULT_BACKEND=redis://localhost:6379/2
scripts\start-celery-worker.cmd
```

## 面试表达

我没有把文件解析和 chunk 入库放在 HTTP 请求里长时间阻塞，而是把它设计为异步任务。上传接口返回 taskId，任务状态记录 pending、queued、running、succeeded、failed，失败后可以基于 textSnapshot retry，管理员后台能看到任务健康状态和失败原因。
```

- [x] **Step 2: Update roadmap current state**

In `docs/roadmap/current-state.md`, under the current active phase or a new dated note, add:

```markdown
Async Worker Readiness V4 开始执行：本阶段聚焦 RAG 文档摄取的 Celery worker readiness、管理员可观测性和运行说明，不重复已完成的 RAG ingestion / Production Hardening 能力。
```

- [x] **Step 3: Run markdown/reference check**

Run:

```powershell
Select-String -Path docs\deployment\celery-worker-readiness.md -Pattern @("TO" + "DO", "TB" + "D", "待" + "定")
```

Expected: no matches.

- [x] **Step 4: Commit Task A4**

```powershell
git add docs/deployment/celery-worker-readiness.md docs/roadmap/current-state.md
git commit -m "docs: explain celery worker readiness"
```

### Task A5: Verify Phase A

**Files:**
- No production file changes unless a test failure requires a fix.

- [x] **Step 1: Run backend focused tests**

```powershell
python -m pytest tests/test_celery_app.py tests/test_admin_routes.py tests/test_rag_ingestion_celery.py -q
```

Expected: PASS.

- [x] **Step 2: Run frontend focused tests**

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: PASS.

- [x] **Step 3: Run full backend tests**

```powershell
python -m pytest -q
```

Expected: PASS.

- [x] **Step 4: Run full frontend tests and build**

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

Expected: PASS.

- [x] **Step 5: Update roadmap after Phase A**

Modify `docs/roadmap/current-state.md`, `docs/specs/README.md`, and `docs/plans/README.md` to say Phase A is complete and Phase B is next.

- [x] **Step 6: Commit Phase A completion docs**

```powershell
git add docs/roadmap/current-state.md docs/specs/README.md docs/plans/README.md
git commit -m "docs: mark async worker readiness complete"
```

---

## Phase B: PostgreSQL Compatibility V4

### Task B1: Strengthen PostgreSQL Configuration Tests

**Files:**
- Modify: `tests/test_database_config.py`
- Modify: `backend_python/database.py` only if tests expose a gap.

- [x] **Step 1: Write failing tests**

Add tests that assert:

```python
def test_postgresql_url_is_identified_without_exposing_password() -> None:
    from backend_python.database import describe_database_url

    result = describe_database_url(
        "postgresql+psycopg://ai_interview:super-secret@localhost:5432/ai_interview",
        auto_init=False,
    )

    assert result["dialect"] == "postgresql"
    assert result["isPostgres"] is True
    assert result["isSqlite"] is False
    assert "super-secret" not in result["maskedUrl"]
    assert result["autoInit"] is False
```

- [x] **Step 2: Run RED**

```powershell
python -m pytest tests/test_database_config.py -q
```

Expected: FAIL only if the current database summary lacks the asserted fields.

- [x] **Step 3: Implement minimal database summary compatibility**

If needed, update `backend_python/database.py` so `describe_database_url()` returns `dialect`, `isPostgres`, `isSqlite`, `maskedUrl`, and `autoInit`.

- [x] **Step 4: Run GREEN**

```powershell
python -m pytest tests/test_database_config.py -q
```

- [x] **Step 5: Commit Task B1**

```powershell
git add backend_python/database.py tests/test_database_config.py
git commit -m "test: cover postgresql database configuration"
```

### Task B2: Document PostgreSQL Optional Path

**Files:**
- Modify: `.env.example`
- Modify: `.env.production.example`
- Create: `docs/deployment/postgresql-compatibility-v4.md`

- [x] **Step 1: Update env examples**

Ensure `.env.example` keeps SQLite default:

```env
DATABASE_URL=sqlite:///./interview_app.db
AUTO_INIT_DB=true
```

Ensure `.env.production.example` includes PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://ai_interview:replace_with_postgres_password@db:5432/ai_interview
AUTO_INIT_DB=false
```

- [x] **Step 2: Add PostgreSQL compatibility doc**

Create `docs/deployment/postgresql-compatibility-v4.md` explaining:

```markdown
# PostgreSQL Compatibility V4

本地开发默认 SQLite，保证启动快、环境简单。生产环境使用 PostgreSQL，适合多人系统、并发读写、事务、复杂查询和后续 pgvector 扩展。

## 不一刀切替换 SQLite 的原因

- Windows 本地安装和服务管理成本更高。
- 测试链路更慢。
- 迁移脚本要求更严。
- 新手开发时容易被数据库连接问题卡住。

## Docker PostgreSQL 示例

```powershell
docker compose up -d db
```

## 面试表达

项目本地默认 SQLite，但数据库配置层支持 PostgreSQL。这样既保留日常开发效率，也具备生产数据库迁移路径。
```

- [x] **Step 3: Run docs placeholder check**

```powershell
Select-String -Path .env.example,.env.production.example,docs\deployment\postgresql-compatibility-v4.md -Pattern @("TO" + "DO", "TB" + "D", "待" + "定")
```

Expected: no matches.

- [x] **Step 4: Commit Task B2**

```powershell
git add .env.example .env.production.example docs/deployment/postgresql-compatibility-v4.md
git commit -m "docs: explain postgresql compatibility path"
```

### Task B3: Verify Phase B

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [x] **Step 1: Run backend config tests**

```powershell
python -m pytest tests/test_database_config.py tests/test_deployment_config.py -q
```

Expected: PASS.

- [x] **Step 2: Run full backend tests**

```powershell
python -m pytest -q
```

Expected: PASS.

- [x] **Step 3: Update roadmap**

Update docs to say PostgreSQL Compatibility V4 is complete and Deployment Integration V4 is next.

- [x] **Step 4: Commit Phase B completion docs**

```powershell
git add docs/roadmap/current-state.md docs/specs/README.md docs/plans/README.md
git commit -m "docs: mark postgresql compatibility complete"
```

---

## Phase C: Deployment Integration V4

### Task C1: Add Deployment Config Coverage

**Files:**
- Modify: `tests/test_deployment_config.py`
- Modify: `docker-compose.yml` only if tests expose a mismatch.
- Modify: `deploy/nginx/ai-interview.conf` only if tests expose a mismatch.

- [ ] **Step 1: Write deployment config tests**

Add tests that parse `docker-compose.yml` as YAML and assert:

```python
def test_compose_contains_app_worker_db_redis_nginx_services() -> None:
    compose = load_compose()
    assert {"app", "worker", "db", "redis", "nginx"}.issubset(set(compose["services"]))


def test_worker_uses_same_image_and_celery_command() -> None:
    compose = load_compose()
    worker = compose["services"]["worker"]
    assert worker["image"] == compose["services"]["app"]["image"]
    assert "celery" in worker["command"]
    assert "backend_python.celery_app.celery_app" in worker["command"]


def test_nginx_mounts_project_reverse_proxy_config() -> None:
    compose = load_compose()
    nginx = compose["services"]["nginx"]
    assert any("deploy/nginx/ai-interview.conf" in volume for volume in nginx["volumes"])
```

If the file has no YAML helper, add:

```python
from pathlib import Path
import yaml


def load_compose() -> dict:
    return yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_deployment_config.py -q
```

Expected: FAIL only if a deployment assumption is not currently covered or config does not match.

- [ ] **Step 3: Fix minimal config mismatch**

If tests reveal mismatches, adjust `docker-compose.yml` or `deploy/nginx/ai-interview.conf` minimally.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest tests/test_deployment_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task C1**

```powershell
git add tests/test_deployment_config.py docker-compose.yml deploy/nginx/ai-interview.conf
git commit -m "test: cover deployment compose graph"
```

### Task C2: Write Deployment Runbook And Checklist

**Files:**
- Create: `docs/deployment/pre-launch-deployment-runbook-v4.md`
- Create: `docs/deployment/pre-launch-checklist-v4.md`

- [ ] **Step 1: Create deployment runbook**

Create `docs/deployment/pre-launch-deployment-runbook-v4.md` with sections:

```markdown
# Pre-Launch Deployment Runbook V4

## 目标架构

Browser -> Nginx -> Vue3 static assets / FastAPI API -> PostgreSQL / Redis / Celery worker

## 本地 Compose 验证

```powershell
docker compose config
docker compose up -d db redis
docker compose up -d app worker nginx
```

## VPS 部署步骤

1. 准备服务器。
2. 安装 Docker 和 Docker Compose。
3. 上传代码或从 GitHub 拉取。
4. 创建 `.env.production`。
5. 启动 PostgreSQL 和 Redis。
6. 启动 FastAPI app 和 Celery worker。
7. 启动 Nginx。
8. 配置域名和 Cloudflare。
9. 配置 HTTPS。

## 故障排查

- 后端启动失败：检查环境变量和数据库连接。
- worker 不消费任务：检查 Redis、CELERY_BROKER_URL、worker 日志。
- Nginx 502：检查 app 容器和 upstream。
- HTTPS 失败：检查 DNS、证书和 Cloudflare 模式。
```

- [ ] **Step 2: Create pre-launch checklist**

Create `docs/deployment/pre-launch-checklist-v4.md` with:

```markdown
# Pre-Launch Checklist V4

- [ ] `.env.production` 不包含占位密钥。
- [ ] `SECRET_KEY` 已替换为强随机值。
- [ ] DashScope API key 没有提交到 Git。
- [ ] PostgreSQL 连接可用。
- [ ] Redis 连接可用。
- [ ] Celery worker 已启动并能消费 RAG ingestion task。
- [ ] Nginx `/api/*` 正确代理到 FastAPI。
- [ ] Vue3 页面可访问。
- [ ] 管理员后台可看到基础设施、RAG ingestion、Agent workflow 状态。
- [ ] 已准备备份和回滚方案。
```

- [ ] **Step 3: Run docs placeholder check**

```powershell
Select-String -Path docs\deployment\pre-launch-deployment-runbook-v4.md,docs\deployment\pre-launch-checklist-v4.md -Pattern @("TO" + "DO", "TB" + "D", "待" + "定")
```

Expected: no matches.

- [ ] **Step 4: Commit Task C2**

```powershell
git add docs/deployment/pre-launch-deployment-runbook-v4.md docs/deployment/pre-launch-checklist-v4.md
git commit -m "docs: add pre-launch deployment runbook"
```

### Task C3: Verify Phase C

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: Run deployment config validation**

```powershell
docker compose config
python -m pytest tests/test_deployment_config.py -q
```

Expected: both pass. If Docker is unavailable, record the exact failure and keep pytest config validation as evidence.

- [ ] **Step 2: Update roadmap**

Update docs to say Deployment Integration V4 is complete and Project Explanation & Resume Pack V1 is next.

- [ ] **Step 3: Commit Phase C completion docs**

```powershell
git add docs/roadmap/current-state.md docs/specs/README.md docs/plans/README.md
git commit -m "docs: mark deployment integration complete"
```

---

## Phase D: Project Explanation & Resume Pack V1

### Task D1: Write Project Overview

**Files:**
- Create: `docs/project-explanation/ai-interview-system-overview.md`

- [ ] **Step 1: Create overview doc**

Create `docs/project-explanation/ai-interview-system-overview.md` with these sections:

```markdown
# AI 模拟面试系统项目总讲解

## 一句话介绍

这是一个面向大学生和社会求职者的 AI 模拟面试系统。用户创建投递档案后，系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 Agent/LangGraph 面试编排链路，生成贴近岗位和个人经历的面试问题，并在结束后生成复盘报告和训练任务。

## 业务背景

应届生缺少真实面试经验，社会求职者也常常不清楚目标岗位考察重点。普通 AI 聊天容易泛泛而谈，难以结合用户简历、岗位 JD 和历史回答持续追问。

## 核心链路

用户注册登录 -> 创建投递档案 -> 上传简历和岗位 JD -> 开始面试 -> 三类 RAG 召回上下文 -> Agent/LangGraph 构造状态和决策 -> LLM 生成下一题 -> 记录 RAG 命中日志和 Agent 决策日志 -> 生成报告 -> 生成训练任务。

## 三类 RAG

- 岗位知识库 RAG：提供岗位 JD、技术栈和业务场景。
- 题库 RAG：提供面试题、考察点和追问模板。
- 候选人画像 RAG：提供简历摘要、历史回答、weakTags 和训练记录。

## Agent / LangGraph

Agent 不只是调用大模型，而是观察当前状态、检索结果、历史回答和训练弱点，再决定下一步是追问、降难度、切换话题还是结束面试。LangGraph mainline 用节点化工作流承接 observe、retrieve、policy、generate 等步骤，classic Agent 保留为 fallback。

## 可观测性

系统记录 RAG 命中日志、Agent 决策日志、workflow trace、runtime audit 和 ingestion task 状态，让管理员能排查是知识库问题、召回问题、Agent 决策问题还是模型生成问题。

## 生产化设计

本地默认 SQLite，生产兼容 PostgreSQL。Redis 用于缓存、限流、token blacklist 和 Celery broker。Celery 用于 RAG 文档摄取等慢任务。Nginx 负责静态资源托管和 API 反向代理。

## 技术取舍

项目没有为了堆技术栈而一开始强制所有组件上线，而是先完成核心业务闭环，再逐步补齐异步任务、限流、幂等、错误脱敏、部署配置和上线文档。
```

- [ ] **Step 2: Placeholder check**

```powershell
Select-String -Path docs\project-explanation\ai-interview-system-overview.md -Pattern @("TO" + "DO", "TB" + "D", "待" + "定")
```

- [ ] **Step 3: Commit Task D1**

```powershell
git add docs/project-explanation/ai-interview-system-overview.md
git commit -m "docs: add project overview explanation"
```

### Task D2: Write Interview Deep-Dive Q&A

**Files:**
- Create: `docs/project-explanation/interview-deep-dive-qa.md`

- [ ] **Step 1: Create Q&A doc**

Create `docs/project-explanation/interview-deep-dive-qa.md` with Q&A entries for:

```markdown
# 项目面试深挖问答库

## 为什么拆三个 RAG？

因为岗位知识、题库、候选人画像的数据来源、更新频率、权限边界和用途不同。拆开后可以分别维护、评估召回质量和记录命中日志，也方便后续扩展。

## Agent 和普通 LLM 调用有什么区别？

普通 LLM 调用主要是输入 prompt 后生成回答。项目里的 Agent 会先观察状态，包括用户档案、历史问答、RAG 命中结果、回答质量和剩余轮次，再决策下一步动作，例如追问、降难度、切换话题或结束面试。

## 为什么需要 Celery？

RAG 文档摄取涉及文件解析、清洗、切 chunk、embedding 和入库，属于慢任务。Celery 把慢任务从 HTTP 请求链路拆出去，接口快速返回 taskId，worker 后台处理，前端和管理员后台查看进度和失败原因。

## 为什么本地 SQLite，生产 PostgreSQL？

SQLite 启动快、适合本地开发和测试。PostgreSQL 更适合多人系统、并发读写、事务和后续扩展。项目保留 SQLite 默认路径，同时提供 PostgreSQL 生产兼容配置。

## 如何排查 RAG 召回质量差？

先看 RAG 命中日志：是否空召回、弱召回、metadata filter 过滤过度或未进入 prompt。再看 evaluation case 指标，例如 Hit@K、MRR、关键词覆盖率。最后看 Agent decision 和 LLM 输出是否正确使用了召回内容。

## 如何避免 AI 黑箱？

通过 RAG 命中日志、Agent 决策日志、workflow trace、runtime audit 和管理员后台，把检索、决策、兜底和生成依据记录下来，方便复盘和调试。
```

- [ ] **Step 2: Placeholder check**

```powershell
Select-String -Path docs\project-explanation\interview-deep-dive-qa.md -Pattern @("TO" + "DO", "TB" + "D", "待" + "定")
```

- [ ] **Step 3: Commit Task D2**

```powershell
git add docs/project-explanation/interview-deep-dive-qa.md
git commit -m "docs: add project interview deep dive qa"
```

### Task D3: Write Resume Materials

**Files:**
- Create: `docs/project-explanation/resume-bullets-python-backend.md`
- Create: `docs/project-explanation/resume-bullets-ai-application.md`
- Create: `docs/project-explanation/project-demo-script.md`

- [ ] **Step 1: Create Python backend resume material**

Create `docs/project-explanation/resume-bullets-python-backend.md`:

```markdown
# Python 后端岗简历项目表达

## 项目名称

AI 模拟面试系统

## 项目描述

基于 FastAPI、SQLAlchemy、Vue3、RAG 和 Agent/LangGraph 构建的 AI 模拟面试系统，支持用户创建投递档案、结合岗位知识库/题库/候选人画像生成面试问题，面试后生成复盘报告和训练任务，并提供管理员后台观测 RAG 命中、Agent 决策和异步任务状态。

## 可选职责表达

- 设计 FastAPI 后端模块，拆分认证、档案、面试、RAG、训练、管理员后台等路由，使用 SQLAlchemy 建模用户、面试记录、RAG 文档、摄取任务和日志数据。
- 设计 RAG 文档摄取链路，支持文件解析、文本清洗、chunk 入库、任务状态持久化、失败原因记录和 retry。
- 引入 Redis/Celery 生产化底座，将 RAG 文档摄取等慢任务从 HTTP 请求链路拆分为后台任务，并在管理员后台展示任务状态。
- 实现 token blacklist、接口限流、错误脱敏、幂等和 retry 并发保护，提高后端安全性和可维护性。
- 编写 pytest 覆盖认证、RAG、Agent、训练任务、管理员后台和部署配置等核心链路。
```

- [ ] **Step 2: Create AI application resume material**

Create `docs/project-explanation/resume-bullets-ai-application.md`:

```markdown
# AI 应用开发岗简历项目表达

## 项目名称

AI 模拟面试系统

## 项目描述

面向大学生和求职者的 AI 模拟面试系统。系统结合岗位知识库 RAG、题库 RAG、候选人画像 RAG 和 Agent/LangGraph 面试工作流，根据用户简历、岗位 JD、历史回答和训练弱点动态生成面试问题，并通过 RAG 命中日志、Agent 决策日志和 workflow trace 提升 AI 应用可观测性。

## 可选职责表达

- 设计三类 RAG 协作链路，将岗位知识、题库内容和候选人画像拆分维护，并通过 hybrid search、rerank、query rewrite 和 evaluation case 提升召回质量。
- 设计 Agent/LangGraph 面试编排链路，根据 agent state、RAG 命中结果、回答质量和训练弱点动态决策追问、降难度、切换话题或结束面试。
- 建设 AI 可观测性能力，记录 RAG 命中日志、Agent 决策日志、runtime audit 和 workflow trace，支持管理员后台定位召回、决策和生成问题。
- 构建面试复盘和训练闭环，根据报告 weakTags 生成专项训练任务，帮助用户从模拟面试进入针对性练习。
```

- [ ] **Step 3: Create demo script**

Create `docs/project-explanation/project-demo-script.md`:

```markdown
# 项目演示脚本

## 1. 登录和档案

登录系统，创建投递档案，录入简历、岗位 JD 和公司信息。

## 2. 开始面试

进入面试页面，系统结合三类 RAG 和候选人档案生成第一道问题。

## 3. 动态追问

用户回答后，后端构造 agent state，LangGraph/Agent 根据历史回答、RAG 命中和回答质量决定下一步动作。

## 4. 查看报告

面试结束后查看复盘报告、weakTags 和逐题反馈。

## 5. 训练闭环

进入训练中心，根据 weakTag 打开专项练习，提交练习后更新掌握度。

## 6. 管理员后台

展示 RAG 命中情况、Agent workflow 观测、基础设施状态和 RAG ingestion 任务状态，说明系统如何避免 AI 黑箱。
```

- [ ] **Step 4: Placeholder check**

```powershell
Select-String -Path docs\project-explanation\*.md -Pattern @("TO" + "DO", "TB" + "D", "待" + "定")
```

- [ ] **Step 5: Commit Task D3**

```powershell
git add docs/project-explanation/resume-bullets-python-backend.md docs/project-explanation/resume-bullets-ai-application.md docs/project-explanation/project-demo-script.md
git commit -m "docs: add resume and demo materials"
```

### Task D4: Final Roadmap Closure

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Move: `docs/specs/active/pre-launch-delivery-roadmap-v4-design.md` to `docs/specs/completed/pre-launch-delivery-roadmap-v4-design.md`
- Move: `docs/plans/active/pre-launch-delivery-roadmap-v4.md` to `docs/plans/completed/pre-launch-delivery-roadmap-v4.md`

- [ ] **Step 1: Run final checks**

```powershell
python -m pytest -q
cd frontend
npm.cmd run test
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 2: Check deployment config**

```powershell
docker compose config
```

Expected: PASS, or if Docker is unavailable, document the exact reason in final status.

- [ ] **Step 3: Move active docs to completed**

Use PowerShell:

```powershell
Move-Item -LiteralPath docs\specs\active\pre-launch-delivery-roadmap-v4-design.md -Destination docs\specs\completed\pre-launch-delivery-roadmap-v4-design.md
Move-Item -LiteralPath docs\plans\active\pre-launch-delivery-roadmap-v4.md -Destination docs\plans\completed\pre-launch-delivery-roadmap-v4.md
```

- [ ] **Step 4: Update README/current-state**

Set active spec/plan to `暂无` and latest completed stage to `Pre-Launch Delivery Roadmap V4`.

- [ ] **Step 5: Commit final closure**

```powershell
git add docs/roadmap/current-state.md docs/specs/README.md docs/plans/README.md docs/specs/completed/pre-launch-delivery-roadmap-v4-design.md docs/plans/completed/pre-launch-delivery-roadmap-v4.md
git commit -m "docs: complete pre-launch delivery roadmap"
```

---

## Plan Self-Review

- Spec coverage:
  - Async Worker Readiness V4: Tasks A1-A5.
  - PostgreSQL Compatibility V4: Tasks B1-B3.
  - Deployment Integration V4: Tasks C1-C3.
  - Project Explanation & Resume Pack V1: Tasks D1-D4.
  - Roadmap/status updates: Tasks A5, B3, C3, D4.
- Placeholder scan:
  - This plan intentionally contains no unfinished placeholder tokens.
- Type consistency:
  - New backend key is consistently named `workerReadiness`.
  - Frontend type and rendering use the same `workerReadiness` object shape.
  - Celery readiness fields use `mode`, `readyForWorker`, `requiresExternalWorker`, `missingRequirements`, and `message`.
