# AI 模拟面试系统产品化 V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the productization V2 path from the spec: user/admin role foundation, training tasks, user training center, admin MVP, Agent training-task awareness, and LangGraph migration documentation.

**Architecture:** Keep the current FastAPI + SQLAlchemy + native HTML/CSS/JS architecture. Add small backend modules for admin and training tasks instead of enlarging interview routes, keep `/api/interview/next-question` compatible, and treat LangGraph as a documented migration target rather than a runtime dependency.

**Tech Stack:** Python, FastAPI, SQLAlchemy, SQLite compatibility migration, Pydantic, pytest, native HTML/CSS/JavaScript, Node `.mjs` frontend tests.

---

## Scope And Execution Rules

This plan implements `docs/superpowers/specs/2026-06-10-productization-v2-training-admin-langgraph-reserve-design.md`.

Do not implement these in this plan:

- Docker, Nginx, or cloud deployment.
- LangGraph or LangChain runtime dependencies.
- React, Vue, Next.js, or a frontend framework migration.
- Complex RBAC, organization permissions, payment, email verification, or SMS.
- Unrelated cleanup or large rewrites.

Repository rule:

- Do not create git commits unless the user explicitly asks. The task checklists include verification steps, but omit commit steps intentionally.

## File Map

Backend files to create:

- `backend_python/routes/admin.py`: admin-only summary, users, RAG documents, RAG logs, Agent logs, and config endpoints.
- `backend_python/routes/training.py`: user training task endpoints.
- `backend_python/training_tasks.py`: service functions for creating, deduplicating, serializing, and updating training tasks.

Backend files to modify:

- `backend_python/db_models.py`: add `User.role`, `User.training_tasks`, and `TrainingTask`.
- `backend_python/database.py`: SQLite compatibility for `users.role` and `training_tasks`.
- `backend_python/auth.py`: add `require_admin_user`.
- `backend_python/routes/auth.py`: include role in auth responses.
- `backend_python/main.py`: register `admin.router` and `training.router`.
- `backend_python/routes/interview.py`: later add `candidateTrainingTasks` to Agent State without changing request/response compatibility.

Frontend files to modify:

- `index.html`: add navigation targets, training center region, and admin region.
- `styles.css`: add training center/admin layout styles with mobile wrapping.
- `app.js`: add role-aware rendering, training API calls, training center interactions, and admin dashboard interactions.

Test files to create or update:

- `tests/test_admin_auth.py`
- `tests/test_admin_routes.py`
- `tests/test_training_tasks.py`
- `tests/test_training_task_generation.py`
- `tests/test_agent_training_tasks.py`
- `tests/frontend_training_center.test.mjs`
- `tests/frontend_admin_dashboard.test.mjs`
- `tests/frontend_admin_permissions.test.mjs`

Learning docs to create:

- `docs/learning/10-用户角色与后台权限MVP怎么设计.md`
- `docs/learning/11-训练任务系统如何承接weakTags.md`
- `docs/learning/12-训练中心前端页面如何拆分.md`
- `docs/learning/13-管理员后台MVP如何设计.md`
- `docs/learning/14-训练任务如何影响Agent决策.md`
- `docs/learning/15-自研Agent如何迁移到LangGraph.md`

Progress file to update after each stage:

- `docs/pre-deployment-progress.md`

---

## Task 0: Baseline Check

**Files:**
- Read: `docs/superpowers/specs/2026-06-10-productization-v2-training-admin-langgraph-reserve-design.md`
- Read: `docs/pre-deployment-progress.md`
- No code changes.

- [x] **Step 1: Run backend baseline**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
All existing backend tests pass, or any existing failure is recorded before new code changes.
```

- [x] **Step 2: Run frontend baseline**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected:

```text
All existing frontend .mjs tests pass, or any existing failure is recorded before new code changes.
```

- [x] **Step 3: Record baseline**

Update `docs/pre-deployment-progress.md` with a short section:

```markdown
## 产品化 V2 执行记录

- 阶段 0：已完成现状体检。
- 后端基线：`python -m pytest -q`，结果记录为实际输出。
- 前端基线：所有 `.mjs` 测试，结果记录为实际输出。
- 本轮仍不做 Docker、Nginx、云服务器上线，不直接引入 LangGraph。
```

---

## Task 1: User Role And Admin Dependency

**Learning point before coding:** 用户角色不是页面按钮控制，而是后端鉴权能力。前端隐藏后台入口只是体验，真正安全边界必须在 `/api/admin/*` 后端接口里用 `require_admin_user` 拦住。

**Files:**
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/database.py`
- Modify: `backend_python/auth.py`
- Modify: `backend_python/routes/auth.py`
- Create: `tests/test_admin_auth.py`

- [x] **Step 1: Write failing backend tests**

Create `tests/test_admin_auth.py`:

```python
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.auth import require_admin_user
from backend_python.database import SessionLocal, init_db
from backend_python.db_models import User
from backend_python.main import app


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    ).json()


def promote_to_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = "admin"
        db.commit()


def test_registered_user_defaults_to_user_role() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    result = register_and_login(client, f"role-user-{suffix}@example.com", f"role_user_{suffix[:8]}")

    assert result["user"]["role"] == "user"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {result['accessToken']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "user"


def test_admin_role_is_returned_after_login() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"role-admin-{suffix}@example.com"
    username = f"role_admin_{suffix[:8]}"
    register_and_login(client, email, username)
    promote_to_admin(email)

    result = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    assert result["user"]["role"] == "admin"


def test_require_admin_user_allows_admin_and_rejects_user() -> None:
    local_app = FastAPI()

    @local_app.get("/admin-only")
    async def admin_only(_: User = Depends(require_admin_user)) -> dict[str, bool]:
        return {"ok": True}

    local_app.dependency_overrides.update(app.dependency_overrides)
    init_db()
    client = TestClient(local_app)

    suffix = uuid4().hex
    user_email = f"admin-dep-user-{suffix}@example.com"
    admin_email = f"admin-dep-admin-{suffix}@example.com"
    user = register_and_login(TestClient(app), user_email, f"admin_dep_user_{suffix[:8]}")
    admin = register_and_login(TestClient(app), admin_email, f"admin_dep_admin_{suffix[:8]}")
    promote_to_admin(admin_email)
    admin = TestClient(app).post("/api/auth/login", json={"email": admin_email, "password": "password123"}).json()

    no_token = client.get("/admin-only")
    user_response = client.get("/admin-only", headers={"Authorization": f"Bearer {user['accessToken']}"})
    admin_response = client.get("/admin-only", headers={"Authorization": f"Bearer {admin['accessToken']}"})

    assert no_token.status_code == 401
    assert user_response.status_code == 403
    assert admin_response.status_code == 200
    assert admin_response.json() == {"ok": True}
```

- [x] **Step 2: Run failing tests**

Run:

```powershell
python -m pytest tests/test_admin_auth.py -q
```

Expected:

```text
Tests fail because User.role and require_admin_user do not exist or role is missing from auth response.
```

- [x] **Step 3: Add role to User model**

Modify `backend_python/db_models.py`:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [x] **Step 4: Add SQLite compatibility for users.role**

Modify `backend_python/database.py` inside `ensure_sqlite_compatibility_schema()` after `table_names` is available:

```python
        if "users" in table_names:
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "role" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)"))
```

- [x] **Step 5: Add require_admin_user**

Modify `backend_python/auth.py`:

```python
def require_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
```

- [x] **Step 6: Return role from auth responses**

Modify `backend_python/routes/auth.py`:

```python
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str = "user"


def user_response(user: User) -> dict:
    return {"id": user.id, "email": user.email, "username": user.username, "role": user.role}
```

- [x] **Step 7: Run role tests**

Run:

```powershell
python -m pytest tests/test_admin_auth.py -q
```

Expected:

```text
3 passed
```

- [x] **Step 8: Run auth/history regression tests**

Run:

```powershell
python -m pytest tests/test_history_auth.py tests/frontend_auth_refresh.test.mjs -q
```

If the `.mjs` file cannot be run through pytest, run:

```powershell
python -m pytest tests/test_history_auth.py -q
node tests/frontend_auth_refresh.test.mjs
```

Expected:

```text
History auth tests pass and auth refresh frontend test passes.
```

---

## Task 2: Admin Summary Route MVP

**Learning point before coding:** 后台接口应先做最小闭环：一个 admin-only summary 能验证角色字段、权限依赖、路由注册和前后端未来入口，不需要一开始做完整后台页面。

**Files:**
- Create: `backend_python/routes/admin.py`
- Modify: `backend_python/main.py`
- Create: `tests/test_admin_routes.py`

- [x] **Step 1: Write failing admin route tests**

Create `tests/test_admin_routes.py`:

```python
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog, InterviewRecord, RagDocument, RagRetrievalLog, User
from backend_python.main import app


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    return client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()


def promote_to_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = "admin"
        db.commit()


def test_admin_summary_requires_admin() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user = register_and_login(client, f"summary-user-{suffix}@example.com", f"summary_user_{suffix[:8]}")

    no_token = client.get("/api/admin/summary")
    user_response = client.get("/api/admin/summary", headers={"Authorization": f"Bearer {user['accessToken']}"})

    assert no_token.status_code == 401
    assert user_response.status_code == 403


def test_admin_summary_returns_platform_counts() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"summary-admin-{suffix}@example.com"
    admin = register_and_login(client, email, f"summary_admin_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    with SessionLocal() as db:
        admin_user = db.scalar(select(User).where(User.email == email))
        assert admin_user is not None
        db.add(
            InterviewRecord(
                user_id=admin_user.id,
                candidate_name="Admin",
                target_role="AI 应用开发",
                application_type="实习",
                mode="技术一面",
                depth="standard",
                score=80,
                profile_json="{}",
                answers_json="[]",
                report_json="{}",
            )
        )
        db.add(
            RagDocument(
                user_id=admin_user.id,
                title="RAG 测试文档",
                knowledge_base="role_knowledge",
                content="RAG 文档",
                metadata_json="{}",
            )
        )
        db.add(
            RagRetrievalLog(
                user_id=admin_user.id,
                request_type="debug",
                query_text="RAG",
                retriever_name="role_knowledge",
                hit_count=1,
                hits_json="[]",
            )
        )
        db.add(
            AgentDecisionLog(
                user_id=admin_user.id,
                request_type="next_question",
                next_action="deepen",
                state_json="{}",
                decision_json="{}",
            )
        )
        db.commit()

    response = client.get("/api/admin/summary", headers={"Authorization": f"Bearer {admin['accessToken']}"})

    assert response.status_code == 200
    body = response.json()
    assert body["userCount"] >= 1
    assert body["interviewRecordCount"] >= 1
    assert body["ragDocumentCount"] >= 1
    assert body["ragRetrievalLogCount"] >= 1
    assert body["agentDecisionLogCount"] >= 1
```

- [x] **Step 2: Run failing tests**

Run:

```powershell
python -m pytest tests/test_admin_routes.py -q
```

Expected:

```text
Tests fail with 404 because /api/admin/summary is not registered.
```

- [x] **Step 3: Create admin router**

Create `backend_python/routes/admin.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_admin_user
from ..config import DASHSCOPE_EMBEDDING_MODEL, DASHSCOPE_RERANK_MODEL, MODEL_NAME
from ..database import get_db
from ..db_models import AgentDecisionLog, InterviewRecord, RagDocument, RagRetrievalLog, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


def count_rows(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


@router.get("/summary")
async def admin_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, int]:
    return {
        "userCount": count_rows(db, User),
        "interviewRecordCount": count_rows(db, InterviewRecord),
        "ragDocumentCount": count_rows(db, RagDocument),
        "ragRetrievalLogCount": count_rows(db, RagRetrievalLog),
        "agentDecisionLogCount": count_rows(db, AgentDecisionLog),
    }


@router.get("/config")
async def admin_config(_: User = Depends(require_admin_user)) -> dict[str, str]:
    return {
        "modelName": MODEL_NAME,
        "embeddingModel": DASHSCOPE_EMBEDDING_MODEL,
        "rerankModel": DASHSCOPE_RERANK_MODEL,
        "database": "configured",
    }
```

- [x] **Step 4: Register admin router**

Modify `backend_python/main.py` imports and router registration:

```python
from .routes import admin, agent, application_profiles, auth, history, interview, memory, position_agent, rag, rag_documents, resume

app.include_router(admin.router)
```

- [x] **Step 5: Run admin route tests**

Run:

```powershell
python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py -q
```

Expected:

```text
All admin auth and admin route tests pass.
```

---

## Task 3: TrainingTask Model And Service

**Learning point before coding:** weakTags 是“诊断标签”，TrainingTask 是“可跟踪任务”。把二者拆开后，系统才能记录任务状态、优先级、掌握度和训练次数。

**Files:**
- Modify: `backend_python/db_models.py`
- Modify: `backend_python/database.py`
- Create: `backend_python/training_tasks.py`
- Create: `tests/test_training_tasks.py`

- [x] **Step 1: Write failing service tests**

Create `tests/test_training_tasks.py`:

```python
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import TrainingTask, User
from backend_python.main import app
from backend_python.training_tasks import complete_training_task, create_or_update_training_task, serialize_training_task


def create_user() -> User:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"training-user-{suffix}@example.com"
    username = f"training_user_{suffix[:8]}"
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        db.expunge(user)
        return user


def test_create_or_update_training_task_deduplicates_active_task() -> None:
    user = create_user()
    with SessionLocal() as db:
        first = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="rag_quality",
            weak_label="RAG 质量评估",
            title="RAG 质量评估基础训练",
            description="练习 Hit@K、MRR 和关键词覆盖率。",
            priority="high",
            mastery_score=30,
            metadata={"source": "report"},
        )
        second = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="rag_quality",
            weak_label="RAG 质量评估",
            title="RAG 质量评估复练",
            description="继续练习 RAG 质量指标。",
            priority="high",
            mastery_score=45,
            metadata={"source": "retry"},
        )
        tasks = db.scalars(select(TrainingTask).where(TrainingTask.user_id == user.id)).all()

    assert first.id == second.id
    assert len(tasks) == 1
    assert tasks[0].title == "RAG 质量评估复练"
    assert tasks[0].mastery_score == 45


def test_complete_training_task_updates_mastery_and_status() -> None:
    user = create_user()
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="agent_state",
            weak_label="Agent 状态决策",
            title="Agent State 训练",
            description="练习 Agent State、ToolCalls 和 Decision。",
            priority="medium",
            mastery_score=70,
            metadata={},
        )
        completed = complete_training_task(db, task.id, user_id=user.id, answer_status="完整")
        data = serialize_training_task(completed)

    assert data["attemptCount"] == 1
    assert data["masteryScore"] == 85
    assert data["status"] == "done"
    assert data["lastPracticedAt"]


def test_complete_training_task_clamps_mastery_score() -> None:
    user = create_user()
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="backend_fastapi",
            weak_label="FastAPI 后端",
            title="FastAPI 训练",
            description="练习后端模块化。",
            priority="high",
            mastery_score=3,
            metadata={},
        )
        completed = complete_training_task(db, task.id, user_id=user.id, answer_status="不会")

    assert completed.mastery_score == 0
    assert completed.status == "in_progress"
```

- [x] **Step 2: Run failing service tests**

Run:

```powershell
python -m pytest tests/test_training_tasks.py -q
```

Expected:

```text
Tests fail because TrainingTask and backend_python.training_tasks do not exist.
```

- [x] **Step 3: Add TrainingTask model**

Modify `backend_python/db_models.py`:

```python
class User(Base):
    ...
    training_tasks: Mapped[list["TrainingTask"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class TrainingTask(Base):
    __tablename__ = "training_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_profile_id: Mapped[int | None] = mapped_column(ForeignKey("application_profiles.id"), nullable=True, index=True)
    source_interview_record_id: Mapped[int | None] = mapped_column(ForeignKey("interview_records.id"), nullable=True, index=True)
    weak_tag: Mapped[str] = mapped_column(String(80), index=True)
    weak_label: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="todo", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="medium", index=True)
    mastery_score: Mapped[int] = mapped_column(Integer, default=40)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="training_tasks")
```

- [x] **Step 4: Add SQLite table compatibility**

Modify `backend_python/database.py`:

```python
        if "training_tasks" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE training_tasks (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        application_profile_id INTEGER,
                        source_interview_record_id INTEGER,
                        weak_tag VARCHAR(80) NOT NULL,
                        weak_label VARCHAR(120) NOT NULL DEFAULT '',
                        title VARCHAR(200) NOT NULL DEFAULT '',
                        description TEXT NOT NULL DEFAULT '',
                        status VARCHAR(40) NOT NULL DEFAULT 'todo',
                        priority VARCHAR(40) NOT NULL DEFAULT 'medium',
                        mastery_score INTEGER NOT NULL DEFAULT 40,
                        attempt_count INTEGER NOT NULL DEFAULT 0,
                        last_practiced_at DATETIME,
                        next_review_at DATETIME,
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users (id),
                        FOREIGN KEY(application_profile_id) REFERENCES application_profiles (id),
                        FOREIGN KEY(source_interview_record_id) REFERENCES interview_records (id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_id ON training_tasks (id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_user_id ON training_tasks (user_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_weak_tag ON training_tasks (weak_tag)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_status ON training_tasks (status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_priority ON training_tasks (priority)"))
```

- [x] **Step 5: Create training task service**

Create `backend_python/training_tasks.py`:

```python
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import TrainingTask

ACTIVE_STATUSES = {"todo", "in_progress", "done"}
VALID_STATUSES = {"todo", "in_progress", "done", "archived"}
VALID_PRIORITIES = {"low", "medium", "high"}
MASTERY_DELTA = {"不会": -5, "模糊": 8, "完整": 15}


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


def normalize_priority(value: str) -> str:
    return value if value in VALID_PRIORITIES else "medium"


def parse_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def serialize_training_task(task: TrainingTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "applicationProfileId": task.application_profile_id,
        "sourceInterviewRecordId": task.source_interview_record_id,
        "weakTag": task.weak_tag,
        "weakLabel": task.weak_label,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "masteryScore": task.mastery_score,
        "attemptCount": task.attempt_count,
        "lastPracticedAt": task.last_practiced_at.isoformat() if task.last_practiced_at else "",
        "nextReviewAt": task.next_review_at.isoformat() if task.next_review_at else "",
        "metadata": parse_json(task.metadata_json, {}),
        "createdAt": task.created_at.isoformat() if task.created_at else "",
        "updatedAt": task.updated_at.isoformat() if task.updated_at else "",
    }


def find_active_task(
    db: Session,
    *,
    user_id: int,
    weak_tag: str,
    application_profile_id: int | None = None,
) -> TrainingTask | None:
    statement = select(TrainingTask).where(
        TrainingTask.user_id == user_id,
        TrainingTask.weak_tag == weak_tag,
        TrainingTask.status.in_(ACTIVE_STATUSES),
    )
    if application_profile_id is None:
        statement = statement.where(TrainingTask.application_profile_id.is_(None))
    else:
        statement = statement.where(TrainingTask.application_profile_id == application_profile_id)
    return db.scalar(statement.order_by(TrainingTask.updated_at.desc(), TrainingTask.id.desc()))


def create_or_update_training_task(
    db: Session,
    *,
    user_id: int,
    weak_tag: str,
    weak_label: str,
    title: str,
    description: str,
    priority: str = "medium",
    mastery_score: int = 40,
    metadata: dict[str, Any] | None = None,
    application_profile_id: int | None = None,
    source_interview_record_id: int | None = None,
) -> TrainingTask:
    task = find_active_task(
        db,
        user_id=user_id,
        weak_tag=weak_tag,
        application_profile_id=application_profile_id,
    )
    if not task:
        task = TrainingTask(user_id=user_id, weak_tag=weak_tag, application_profile_id=application_profile_id)
        db.add(task)
    task.source_interview_record_id = source_interview_record_id or task.source_interview_record_id
    task.weak_label = weak_label
    task.title = title
    task.description = description
    task.priority = normalize_priority(priority)
    task.mastery_score = clamp_score(mastery_score)
    task.metadata_json = dump_json(metadata or {})
    task.updated_at = utc_now_naive()
    db.commit()
    db.refresh(task)
    return task


def get_owned_training_task(db: Session, task_id: int, *, user_id: int) -> TrainingTask:
    task = db.scalar(select(TrainingTask).where(TrainingTask.id == task_id, TrainingTask.user_id == user_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training task not found")
    return task


def complete_training_task(db: Session, task_id: int, *, user_id: int, answer_status: str) -> TrainingTask:
    task = get_owned_training_task(db, task_id, user_id=user_id)
    delta = MASTERY_DELTA.get(answer_status, 0)
    task.mastery_score = clamp_score(task.mastery_score + delta)
    task.attempt_count += 1
    task.last_practiced_at = utc_now_naive()
    task.updated_at = utc_now_naive()
    if task.mastery_score >= 80:
        task.status = "done"
    else:
        task.status = "in_progress"
    db.commit()
    db.refresh(task)
    return task
```

- [x] **Step 6: Run service tests**

Run:

```powershell
python -m pytest tests/test_training_tasks.py -q
```

Expected:

```text
3 passed
```

---

## Task 4: Training Task API

**Learning point before coding:** service 层负责业务规则，route 层负责 HTTP 入参、鉴权、调用 service、返回响应。这样接口不会越写越胖。

**Files:**
- Create: `backend_python/routes/training.py`
- Modify: `backend_python/main.py`
- Create: `tests/test_training_task_generation.py`

- [x] **Step 1: Write failing API tests**

Create `tests/test_training_task_generation.py`:

```python
from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.main import app


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    return client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()


def test_training_tasks_require_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/training/tasks")

    assert response.status_code == 401


def test_generate_training_tasks_from_report_weak_tags_and_deduplicate() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user = register_and_login(client, f"training-api-{suffix}@example.com", f"training_api_{suffix[:8]}")
    headers = {"Authorization": f"Bearer {user['accessToken']}"}
    payload = {
        "report": {
            "questionReviews": [
                {"focus": "RAG 质量评估", "weakTags": ["rag_quality"]},
                {"focus": "Agent State", "weakTags": ["agent_state", "rag_quality"]},
            ],
            "trainingPlan": {
                "weakTopics": [
                    {"focus": "RAG 质量评估", "weakTags": ["rag_quality"], "trainingAction": "练习 Hit@K 和 MRR"}
                ]
            },
        }
    }

    first = client.post("/api/training/tasks/generate-from-report", headers=headers, json=payload)
    second = client.post("/api/training/tasks/generate-from-report", headers=headers, json=payload)
    listing = client.get("/api/training/tasks", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert listing.status_code == 200
    body = listing.json()
    weak_tags = sorted(item["weakTag"] for item in body["items"])
    assert weak_tags == ["agent_state", "rag_quality"]
    assert len(body["items"]) == 2
    assert all(item["masteryScore"] <= 60 for item in body["items"])


def test_training_task_lifecycle_endpoints_are_user_isolated() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user_a = register_and_login(client, f"task-a-{suffix}@example.com", f"task_a_{suffix[:8]}")
    user_b = register_and_login(client, f"task-b-{suffix}@example.com", f"task_b_{suffix[:8]}")
    headers_a = {"Authorization": f"Bearer {user_a['accessToken']}"}
    headers_b = {"Authorization": f"Bearer {user_b['accessToken']}"}

    created = client.post(
        "/api/training/tasks/generate-from-report",
        headers=headers_a,
        json={"report": {"questionReviews": [{"focus": "RAG", "weakTags": ["rag_quality"]}]}},
    ).json()["items"][0]
    task_id = created["id"]

    forbidden = client.post(f"/api/training/tasks/{task_id}/start", headers=headers_b)
    started = client.post(f"/api/training/tasks/{task_id}/start", headers=headers_a)
    completed = client.post(f"/api/training/tasks/{task_id}/complete", headers=headers_a, json={"answerStatus": "完整"})
    archived = client.post(f"/api/training/tasks/{task_id}/archive", headers=headers_a)

    assert forbidden.status_code == 404
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert completed.status_code == 200
    assert completed.json()["attemptCount"] == 1
    assert completed.json()["masteryScore"] > created["masteryScore"]
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
```

- [x] **Step 2: Run failing API tests**

Run:

```powershell
python -m pytest tests/test_training_task_generation.py -q
```

Expected:

```text
Tests fail with 404 because /api/training/tasks routes do not exist.
```

- [x] **Step 3: Add route schemas and helpers**

Create `backend_python/routes/training.py`:

```python
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..db_models import TrainingTask, User
from ..training_tags import normalize_weak_tags
from ..training_tasks import (
    complete_training_task,
    create_or_update_training_task,
    get_owned_training_task,
    serialize_training_task,
    utc_now_naive,
)
from ..weakness_training_templates import get_training_template

router = APIRouter(prefix="/api/training/tasks", tags=["training"])


class GenerateFromReportRequest(BaseModel):
    applicationProfileId: int | None = None
    sourceInterviewRecordId: int | None = None
    report: dict[str, Any] = Field(default_factory=dict)


class CompleteTaskRequest(BaseModel):
    answerStatus: str = "模糊"


def weak_label_for_tag(weak_tag: str) -> str:
    template = get_training_template(weak_tag)
    return str(template.get("label") or weak_tag) if template else weak_tag


def task_title_for_tag(weak_tag: str) -> str:
    return f"{weak_label_for_tag(weak_tag)}专项训练"


def task_description_for_tag(weak_tag: str) -> str:
    template = get_training_template(weak_tag)
    if template:
        return str(template.get("description") or f"围绕 {weak_label_for_tag(weak_tag)} 补齐项目表达。")
    return f"围绕 {weak_tag} 补齐项目表达。"


def collect_report_weak_tags(report: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for item in report.get("questionReviews") or []:
        tags.extend(normalize_weak_tags(item.get("weakTags")))
    training_plan = report.get("trainingPlan") if isinstance(report.get("trainingPlan"), dict) else {}
    for item in training_plan.get("weakTopics") or []:
        tags.extend(normalize_weak_tags(item.get("weakTags")))
    return list(dict.fromkeys(tags))


@router.get("")
async def list_training_tasks(
    status: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    statement = select(TrainingTask).where(TrainingTask.user_id == current_user.id)
    if status:
        statement = statement.where(TrainingTask.status == status)
    tasks = db.scalars(statement.order_by(TrainingTask.updated_at.desc(), TrainingTask.id.desc())).all()
    return {"items": [serialize_training_task(task) for task in tasks]}


@router.post("/generate-from-report")
async def generate_from_report(
    payload: GenerateFromReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    tasks = []
    for weak_tag in collect_report_weak_tags(payload.report):
        task = create_or_update_training_task(
            db,
            user_id=current_user.id,
            application_profile_id=payload.applicationProfileId,
            source_interview_record_id=payload.sourceInterviewRecordId,
            weak_tag=weak_tag,
            weak_label=weak_label_for_tag(weak_tag),
            title=task_title_for_tag(weak_tag),
            description=task_description_for_tag(weak_tag),
            priority="high",
            mastery_score=45,
            metadata={"source": "report", "reportWeakTag": weak_tag},
        )
        tasks.append(task)
    return {"items": [serialize_training_task(task) for task in tasks]}


@router.get("/{task_id}")
async def get_training_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return serialize_training_task(get_owned_training_task(db, task_id, user_id=current_user.id))


@router.post("/{task_id}/start")
async def start_training_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    task = get_owned_training_task(db, task_id, user_id=current_user.id)
    task.status = "in_progress"
    task.updated_at = utc_now_naive()
    db.commit()
    db.refresh(task)
    return serialize_training_task(task)


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: int,
    payload: CompleteTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return serialize_training_task(
        complete_training_task(db, task_id, user_id=current_user.id, answer_status=payload.answerStatus)
    )


@router.post("/{task_id}/archive")
async def archive_training_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    task = get_owned_training_task(db, task_id, user_id=current_user.id)
    task.status = "archived"
    task.updated_at = utc_now_naive()
    db.commit()
    db.refresh(task)
    return serialize_training_task(task)
```

- [x] **Step 4: Register training router**

Modify `backend_python/main.py`:

```python
from .routes import admin, agent, application_profiles, auth, history, interview, memory, position_agent, rag, rag_documents, resume, training

app.include_router(training.router)
```

- [x] **Step 5: Run training API tests**

Run:

```powershell
python -m pytest tests/test_training_tasks.py tests/test_training_task_generation.py -q
```

Expected:

```text
All training task service and route tests pass.
```

---

## Task 5: User Training Center Frontend

**Learning point before coding:** 前端页面拆分不是换框架，而是把“面试、训练、历史、档案”变成清晰的工作区。原生 JS 也可以用稳定状态对象和渲染函数做产品化页面。

**Files:**
- Modify: `index.html`
- Modify: `styles.css`
- Modify: `app.js`
- Create: `tests/frontend_training_center.test.mjs`

- [x] **Step 1: Write failing frontend training test**

Create `tests/frontend_training_center.test.mjs`:

```javascript
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function createElementStub() {
  return {
    value: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
    dataset: {},
    files: [],
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener() {},
    querySelectorAll() { return []; },
    closest() { return null; },
    scrollIntoView() {},
    focus() {},
  };
}

const elements = new Map();
function getElement(selector) {
  if (!elements.has(selector)) elements.set(selector, createElementStub());
  return elements.get(selector);
}

const calls = [];
const context = {
  console,
  crypto: { randomUUID: () => "test-id" },
  document: { querySelector: (selector) => getElement(selector) },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  fetch: async (url, options = {}) => {
    calls.push({ url, options });
    if (url === "/api/training/tasks") {
      return {
        ok: true,
        status: 200,
        async json() {
          return {
            items: [
              {
                id: 7,
                weakTag: "rag_quality",
                weakLabel: "RAG 质量评估",
                title: "RAG 质量评估专项训练",
                description: "练习 Hit@K、MRR 和关键词覆盖率。",
                status: "todo",
                priority: "high",
                masteryScore: 45,
                attemptCount: 0,
                metadata: { source: "report" },
              },
            ],
          };
        },
      };
    }
    return { ok: true, status: 200, async json() { return { id: 7, status: "in_progress", masteryScore: 45 }; } };
  },
  FormData: class FormData { append() {} },
  URLSearchParams,
  Intl,
  Date,
  Error,
};

const appCode = fs.readFileSync("app.js", "utf8").replace(/loadAuthState\(\);[\s\S]*$/s, "");
const testCode = `
(async () => {
  authState.accessToken = "access-token";
  authState.user = { id: 1, email: "student@example.com", username: "student", role: "user" };
  await loadTrainingTasks();
  renderTrainingCenter();
  globalThis.__result = {
    html: trainingTaskList.innerHTML + trainingTaskDetail.innerHTML,
    calls: globalThis.calls,
  };
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.equal(calls[0].url, "/api/training/tasks");
assert.match(context.__result.html, /RAG 质量评估专项训练/);
assert.match(context.__result.html, /45/);
assert.match(context.__result.html, /high|高优先级/);
assert.match(context.__result.html, /开始训练/);
assert.doesNotMatch(context.__result.html, /undefined/);
```

- [x] **Step 2: Run failing frontend training test**

Run:

```powershell
node tests/frontend_training_center.test.mjs
```

Expected:

```text
Test fails because trainingTaskList, trainingTaskDetail, loadTrainingTasks, or renderTrainingCenter is missing.
```

- [x] **Step 3: Add training center markup**

Modify `index.html` with stable IDs:

```html
<section class="workspace-panel training-center-panel" id="trainingCenterPanel" aria-label="薄弱点训练中心">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Training Center</p>
      <h2>薄弱点训练</h2>
    </div>
    <button class="secondary-button" id="trainingRefreshButton" type="button">刷新任务</button>
  </div>
  <div class="training-center-layout">
    <div class="training-task-list" id="trainingTaskList"></div>
    <div class="training-task-detail" id="trainingTaskDetail"></div>
  </div>
</section>
```

- [x] **Step 4: Add training state and render functions**

Modify `app.js`:

```javascript
const trainingRefreshButton = document.querySelector("#trainingRefreshButton");
const trainingTaskList = document.querySelector("#trainingTaskList");
const trainingTaskDetail = document.querySelector("#trainingTaskDetail");

session.training = {
  tasks: [],
  selectedTaskId: null,
};

function priorityLabel(priority) {
  return { high: "高优先级", medium: "中优先级", low: "低优先级" }[priority] || "中优先级";
}

async function loadTrainingTasks() {
  if (!isLoggedIn()) {
    session.training.tasks = [];
    renderTrainingCenter();
    return;
  }
  const result = await requestJson("/api/training/tasks", {}, { auth: true });
  session.training.tasks = Array.isArray(result.items) ? result.items : [];
  if (!session.training.selectedTaskId && session.training.tasks.length) {
    session.training.selectedTaskId = session.training.tasks[0].id;
  }
  renderTrainingCenter();
}

function selectedTrainingTask() {
  return session.training.tasks.find((task) => task.id === session.training.selectedTaskId) || session.training.tasks[0] || null;
}

function renderTrainingCenter() {
  if (!trainingTaskList || !trainingTaskDetail) return;
  if (!isLoggedIn()) {
    trainingTaskList.innerHTML = `<p class="empty-state">登录后可以查看薄弱点训练任务。</p>`;
    trainingTaskDetail.innerHTML = "";
    return;
  }
  if (!session.training.tasks.length) {
    trainingTaskList.innerHTML = `<p class="empty-state">暂无训练任务，可以先完成一次面试复盘。</p>`;
    trainingTaskDetail.innerHTML = "";
    return;
  }
  trainingTaskList.innerHTML = session.training.tasks
    .map((task) => `
      <button class="training-task-card ${task.id === session.training.selectedTaskId ? "active" : ""}" type="button" data-training-task-id="${task.id}">
        <strong>${task.title}</strong>
        <span>${task.weakLabel || task.weakTag}</span>
        <small>${priorityLabel(task.priority)} · 掌握度 ${task.masteryScore}</small>
      </button>
    `)
    .join("");

  const task = selectedTrainingTask();
  trainingTaskDetail.innerHTML = `
    <article class="training-detail-card">
      <p class="eyebrow">${task.weakTag}</p>
      <h3>${task.title}</h3>
      <p>${task.description || "围绕该薄弱点完成专项训练。"}</p>
      <div class="training-meta-row">
        <span>状态：${task.status}</span>
        <span>掌握度：${task.masteryScore}</span>
        <span>训练次数：${task.attemptCount}</span>
      </div>
      <div class="training-actions">
        <button class="primary-button" type="button" data-training-start="${task.id}">开始训练</button>
        <button class="secondary-button" type="button" data-training-complete="${task.id}">标记完成</button>
        <button class="ghost-button" type="button" data-training-archive="${task.id}">归档</button>
      </div>
    </article>
  `;
}
```

- [x] **Step 5: Add event handling**

Modify `app.js` near existing event listeners:

```javascript
trainingRefreshButton?.addEventListener("click", () => loadTrainingTasks());

trainingTaskList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-training-task-id]");
  if (!button) return;
  session.training.selectedTaskId = Number(button.dataset.trainingTaskId);
  renderTrainingCenter();
});

trainingTaskDetail?.addEventListener("click", async (event) => {
  const startButton = event.target.closest("[data-training-start]");
  const completeButton = event.target.closest("[data-training-complete]");
  const archiveButton = event.target.closest("[data-training-archive]");
  const taskId = Number(startButton?.dataset.trainingStart || completeButton?.dataset.trainingComplete || archiveButton?.dataset.trainingArchive || 0);
  if (!taskId) return;
  if (startButton) await requestJson(`/api/training/tasks/${taskId}/start`, {}, { auth: true });
  if (completeButton) await requestJson(`/api/training/tasks/${taskId}/complete`, { answerStatus: "完整" }, { auth: true });
  if (archiveButton) await requestJson(`/api/training/tasks/${taskId}/archive`, {}, { auth: true });
  await loadTrainingTasks();
});
```

- [x] **Step 6: Add training styles**

Modify `styles.css`:

```css
.training-center-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(0, 1.2fr);
  gap: 16px;
}

.training-task-list {
  display: grid;
  gap: 10px;
}

.training-task-card {
  width: 100%;
  text-align: left;
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  border-radius: 8px;
  padding: 12px;
}

.training-task-card.active {
  border-color: var(--accent-color);
}

.training-detail-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  background: var(--surface-color);
}

.training-meta-row,
.training-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 760px) {
  .training-center-layout {
    grid-template-columns: 1fr;
  }
}
```

- [x] **Step 7: Run frontend training test**

Run:

```powershell
node tests/frontend_training_center.test.mjs
```

Expected:

```text
No assertion failures.
```

---

## Task 6: Upgrade One-Click Weak Topic Retry To Generate Training Tasks

**Learning point before coding:** “一键重练”以前只是把弱点塞回下一轮面试上下文，现在要升级成持久化训练任务，这样用户第二天还能看到自己该练什么。

**Files:**
- Modify: `app.js`
- Update: `tests/frontend_interview_flow.test.mjs`

- [x] **Step 1: Update frontend interview flow expectation**

In `tests/frontend_interview_flow.test.mjs`, extend the fake fetch and assertions so `startWeakTopicRetry()` calls:

```text
POST /api/training/tasks/generate-from-report
GET /api/training/tasks
```

Expected request body:

```javascript
assert.equal(trainingTaskCall.url, "/api/training/tasks/generate-from-report");
assert.match(trainingTaskCall.options.body, /rag_quality|RAG 召回链路/);
```

- [x] **Step 2: Run failing frontend flow test**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
```

Expected:

```text
Test fails because one-click retry does not call training task generation yet.
```

- [x] **Step 3: Modify startWeakTopicRetry**

Modify `app.js` inside `startWeakTopicRetry(trainingPlan)` before starting retry interview:

```javascript
async function generateTrainingTasksFromLatestReport() {
  if (!isLoggedIn() || !session.latestReport) return;
  await requestJson(
    "/api/training/tasks/generate-from-report",
    {
      applicationProfileId: session.selectedProfileId || null,
      sourceInterviewRecordId: session.savedReportId || null,
      report: session.latestReport,
    },
    { auth: true }
  );
  await loadTrainingTasks();
}
```

Call it:

```javascript
await generateTrainingTasksFromLatestReport();
```

- [x] **Step 4: Run frontend flow tests**

Run:

```powershell
node tests/frontend_interview_flow.test.mjs
node tests/frontend_training_center.test.mjs
```

Expected:

```text
Both tests pass.
```

---

## Task 7: Admin Backend Lists

**Learning point before coding:** 后台 MVP 先做只读列表，可以快速建立管理面，而不引入危险的删除、封禁、强制下线等高风险操作。

**Files:**
- Modify: `backend_python/routes/admin.py`
- Update: `tests/test_admin_routes.py`

- [x] **Step 1: Add failing admin list tests**

Append to `tests/test_admin_routes.py`:

```python
def test_admin_can_list_users_and_logs() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"admin-list-{suffix}@example.com"
    register_and_login(client, email, f"admin_list_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {admin['accessToken']}"}

    users = client.get("/api/admin/users", headers=headers)
    rag_logs = client.get("/api/admin/rag/logs", headers=headers)
    agent_logs = client.get("/api/admin/agent/logs", headers=headers)
    documents = client.get("/api/admin/rag/documents", headers=headers)
    config = client.get("/api/admin/config", headers=headers)

    assert users.status_code == 200
    assert rag_logs.status_code == 200
    assert agent_logs.status_code == 200
    assert documents.status_code == 200
    assert config.status_code == 200
    assert "items" in users.json()
    assert "items" in rag_logs.json()
    assert "items" in agent_logs.json()
    assert "items" in documents.json()
    assert "modelName" in config.json()
```

- [x] **Step 2: Run failing admin list tests**

Run:

```powershell
python -m pytest tests/test_admin_routes.py -q
```

Expected:

```text
Tests fail because admin list endpoints are missing.
```

- [x] **Step 3: Add serializers and list endpoints**

Modify `backend_python/routes/admin.py`:

```python
from ..agent_logging import serialize_agent_decision_log
from ..rag_logging import serialize_rag_retrieval_log
from ..rag_store import serialize_document


def serialize_admin_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "createdAt": user.created_at.isoformat() if user.created_at else "",
    }


@router.get("/users")
async def admin_users(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict:
    safe_limit = min(max(limit, 1), 100)
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc()).limit(safe_limit)).all()
    return {"items": [serialize_admin_user(user) for user in users]}


@router.get("/rag/documents")
async def admin_rag_documents(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict:
    safe_limit = min(max(limit, 1), 100)
    documents = db.scalars(select(RagDocument).order_by(RagDocument.updated_at.desc(), RagDocument.id.desc()).limit(safe_limit)).all()
    return {"items": [serialize_document(document) for document in documents]}


@router.get("/rag/logs")
async def admin_rag_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict:
    safe_limit = min(max(limit, 1), 100)
    logs = db.scalars(select(RagRetrievalLog).order_by(RagRetrievalLog.created_at.desc(), RagRetrievalLog.id.desc()).limit(safe_limit)).all()
    return {"items": [serialize_rag_retrieval_log(log) for log in logs]}


@router.get("/agent/logs")
async def admin_agent_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict:
    safe_limit = min(max(limit, 1), 100)
    logs = db.scalars(select(AgentDecisionLog).order_by(AgentDecisionLog.created_at.desc(), AgentDecisionLog.id.desc()).limit(safe_limit)).all()
    return {"items": [serialize_agent_decision_log(log) for log in logs]}
```

- [x] **Step 4: Run admin backend tests**

Run:

```powershell
python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py -q
```

Expected:

```text
All admin tests pass.
```

---

## Task 8: Admin Frontend Entry And Dashboard

**Learning point before coding:** 前端是否显示后台入口只能改善体验，不能代替后端权限。这里的前端目标是让 admin 看得到入口，让普通 user 看不到入口，真正拦截仍由后端测试保证。

**Files:**
- Modify: `index.html`
- Modify: `styles.css`
- Modify: `app.js`
- Create: `tests/frontend_admin_permissions.test.mjs`
- Create: `tests/frontend_admin_dashboard.test.mjs`

- [x] **Step 1: Write admin permission frontend test**

Create `tests/frontend_admin_permissions.test.mjs`:

```javascript
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function createElementStub() {
  return {
    value: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
    dataset: {},
    classList: { added: [], removed: [], add(value) { this.added.push(value); }, remove(value) { this.removed.push(value); }, toggle() {} },
    addEventListener() {},
    querySelectorAll() { return []; },
    closest() { return null; },
  };
}

const elements = new Map();
function getElement(selector) {
  if (!elements.has(selector)) elements.set(selector, createElementStub());
  return elements.get(selector);
}

const context = {
  console,
  document: { querySelector: (selector) => getElement(selector) },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  fetch: async () => ({ ok: true, status: 200, async json() { return {}; } }),
  FormData: class FormData { append() {} },
  URLSearchParams,
  Intl,
  Date,
  Error,
};

const appCode = fs.readFileSync("app.js", "utf8").replace(/loadAuthState\(\);[\s\S]*$/s, "");
const testCode = `
authState.user = { id: 1, email: "u@example.com", username: "user", role: "user" };
renderAdminVisibility();
const userHtml = adminNavButton.classList.added.join(",");
authState.user = { id: 2, email: "a@example.com", username: "admin", role: "admin" };
renderAdminVisibility();
globalThis.__result = {
  userAdded: userHtml,
  adminRemoved: adminNavButton.classList.removed.join(","),
};
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.match(context.__result.userAdded, /hidden/);
assert.match(context.__result.adminRemoved, /hidden/);
```

- [x] **Step 2: Write admin dashboard frontend test**

Create `tests/frontend_admin_dashboard.test.mjs`:

```javascript
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function createElementStub() {
  return {
    value: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
    dataset: {},
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener() {},
    querySelectorAll() { return []; },
    closest() { return null; },
  };
}

const elements = new Map();
function getElement(selector) {
  if (!elements.has(selector)) elements.set(selector, createElementStub());
  return elements.get(selector);
}

const calls = [];
const context = {
  console,
  calls,
  document: { querySelector: (selector) => getElement(selector) },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  fetch: async (url, options = {}) => {
    calls.push({ url, options });
    const payloads = {
      "/api/admin/summary": { userCount: 2, interviewRecordCount: 3, ragDocumentCount: 4, ragRetrievalLogCount: 5, agentDecisionLogCount: 6 },
      "/api/admin/users": { items: [{ id: 1, email: "admin@example.com", username: "admin", role: "admin" }] },
      "/api/admin/rag/logs": { items: [{ id: 9, retrieverName: "role_knowledge", queryText: "RAG", hitCount: 2 }] },
      "/api/admin/agent/logs": { items: [{ id: 10, nextAction: "deepen", focus: "Agent State", reason: "回答完整" }] },
      "/api/admin/rag/documents": { items: [{ id: 11, title: "岗位知识", knowledgeBase: "role_knowledge" }] },
    };
    return { ok: true, status: 200, async json() { return payloads[url] || {}; } };
  },
  FormData: class FormData { append() {} },
  URLSearchParams,
  Intl,
  Date,
  Error,
};

const appCode = fs.readFileSync("app.js", "utf8").replace(/loadAuthState\(\);[\s\S]*$/s, "");
const testCode = `
(async () => {
  authState.accessToken = "access-token";
  authState.user = { id: 2, email: "admin@example.com", username: "admin", role: "admin" };
  await loadAdminDashboard();
  globalThis.__result = {
    html: adminDashboardContent.innerHTML,
    calls: globalThis.calls.map((call) => call.url),
  };
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.deepEqual(context.__result.calls.slice(0, 5), [
  "/api/admin/summary",
  "/api/admin/users",
  "/api/admin/rag/documents",
  "/api/admin/rag/logs",
  "/api/admin/agent/logs",
]);
assert.match(context.__result.html, /用户总数/);
assert.match(context.__result.html, /admin@example.com/);
assert.match(context.__result.html, /岗位知识/);
assert.match(context.__result.html, /role_knowledge/);
assert.match(context.__result.html, /deepen/);
assert.doesNotMatch(context.__result.html, /undefined/);
```

- [x] **Step 3: Run failing admin frontend tests**

Run:

```powershell
node tests/frontend_admin_permissions.test.mjs
node tests/frontend_admin_dashboard.test.mjs
```

Expected:

```text
Tests fail because adminNavButton, adminDashboardContent, renderAdminVisibility, or loadAdminDashboard are missing.
```

- [x] **Step 4: Add admin markup**

Modify `index.html`:

```html
<button class="nav-button hidden" id="adminNavButton" type="button">后台</button>

<section class="workspace-panel admin-dashboard-panel hidden" id="adminDashboardPanel" aria-label="后台管理">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Admin</p>
      <h2>后台管理</h2>
    </div>
    <button class="secondary-button" id="adminRefreshButton" type="button">刷新后台</button>
  </div>
  <div id="adminDashboardContent"></div>
</section>
```

- [x] **Step 5: Add admin JS**

Modify `app.js`:

```javascript
const adminNavButton = document.querySelector("#adminNavButton");
const adminRefreshButton = document.querySelector("#adminRefreshButton");
const adminDashboardContent = document.querySelector("#adminDashboardContent");

session.admin = {
  summary: null,
  users: [],
  documents: [],
  ragLogs: [],
  agentLogs: [],
};

function isAdminUser() {
  return authState.user?.role === "admin";
}

function renderAdminVisibility() {
  if (!adminNavButton) return;
  if (isAdminUser()) {
    adminNavButton.classList.remove("hidden");
  } else {
    adminNavButton.classList.add("hidden");
  }
}

async function loadAdminDashboard() {
  if (!isAdminUser()) {
    if (adminDashboardContent) adminDashboardContent.innerHTML = `<p class="empty-state">需要管理员权限。</p>`;
    return;
  }
  const [summary, users, documents, ragLogs, agentLogs] = await Promise.all([
    requestJson("/api/admin/summary", {}, { auth: true }),
    requestJson("/api/admin/users", {}, { auth: true }),
    requestJson("/api/admin/rag/documents", {}, { auth: true }),
    requestJson("/api/admin/rag/logs", {}, { auth: true }),
    requestJson("/api/admin/agent/logs", {}, { auth: true }),
  ]);
  session.admin = {
    summary,
    users: users.items || [],
    documents: documents.items || [],
    ragLogs: ragLogs.items || [],
    agentLogs: agentLogs.items || [],
  };
  renderAdminDashboard();
}

function renderAdminDashboard() {
  if (!adminDashboardContent) return;
  const summary = session.admin.summary || {};
  adminDashboardContent.innerHTML = `
    <div class="admin-summary-grid">
      <article><span>用户总数</span><strong>${summary.userCount || 0}</strong></article>
      <article><span>面试记录</span><strong>${summary.interviewRecordCount || 0}</strong></article>
      <article><span>RAG 文档</span><strong>${summary.ragDocumentCount || 0}</strong></article>
      <article><span>RAG 日志</span><strong>${summary.ragRetrievalLogCount || 0}</strong></article>
      <article><span>Agent 日志</span><strong>${summary.agentDecisionLogCount || 0}</strong></article>
    </div>
    <section class="admin-list-section">
      <h3>用户</h3>
      ${session.admin.users.map((user) => `<p>${user.email} · ${user.role}</p>`).join("") || "<p>暂无用户</p>"}
    </section>
    <section class="admin-list-section">
      <h3>RAG 文档</h3>
      ${session.admin.documents.map((document) => `<p>${document.title} · ${document.knowledgeBase}</p>`).join("") || "<p>暂无文档</p>"}
    </section>
    <section class="admin-list-section">
      <h3>RAG 日志</h3>
      ${session.admin.ragLogs.map((log) => `<p>${log.retrieverName} · ${log.queryText || ""} · 命中 ${log.hitCount || 0}</p>`).join("") || "<p>暂无日志</p>"}
    </section>
    <section class="admin-list-section">
      <h3>Agent 日志</h3>
      ${session.admin.agentLogs.map((log) => `<p>${log.nextAction} · ${log.focus || ""} · ${log.reason || ""}</p>`).join("") || "<p>暂无日志</p>"}
    </section>
  `;
}
```

- [x] **Step 6: Call renderAdminVisibility after auth changes**

Modify `renderAuthState()` and auth lifecycle after user changes:

```javascript
renderAdminVisibility();
```

Call it after:

- login success.
- logout.
- `/api/auth/me` refresh.
- initial load after `loadAuthState()`.

- [x] **Step 7: Add admin styles**

Modify `styles.css`:

```css
.admin-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.admin-summary-grid article,
.admin-list-section {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  background: var(--surface-color);
}

.admin-list-section p {
  overflow-wrap: anywhere;
}
```

- [x] **Step 8: Run admin frontend tests**

Run:

```powershell
node tests/frontend_admin_permissions.test.mjs
node tests/frontend_admin_dashboard.test.mjs
```

Expected:

```text
No assertion failures.
```

---

## Task 9: Agent Reads Candidate Training Tasks

**Learning point before coding:** 训练任务进入 Agent State 后，只是辅助决策信号，不应该替代 RAG、weaknessStrategy 或 guardrail。这样能增强个性化，又不破坏现有面试主流程。

**Files:**
- Modify: `backend_python/training_tasks.py`
- Modify: `backend_python/routes/interview.py`
- Update: `tests/test_agent_training_tasks.py`
- Update: `tests/test_interview_agent_route.py`

- [x] **Step 1: Write failing Agent training-task test**

Create `tests/test_agent_training_tasks.py`:

```python
import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog, User
from backend_python.main import app
from backend_python.training_tasks import create_or_update_training_task


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    return client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()


def test_next_question_agent_state_includes_high_priority_training_tasks(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 质量评估",
                "reason": "候选人存在低掌握度训练任务。",
                "tools": ["retrieve_context"],
                "shouldUpdateMemory": True,
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "RAG 质量评估",
            "prompt": "我们先拆小一点：Hit@K 解决什么问题？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"agent-training-{suffix}@example.com"
    user = register_and_login(client, email, f"agent_training_{suffix[:8]}")

    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        assert user_id is not None
        create_or_update_training_task(
            db,
            user_id=user_id,
            weak_tag="rag_quality",
            weak_label="RAG 质量评估",
            title="RAG 质量评估专项训练",
            description="练习 Hit@K 和 MRR。",
            priority="high",
            mastery_score=45,
            metadata={"source": "test"},
        )

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {user['accessToken']}"},
        json={
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG"},
            "history": [{"question": "RAG 质量怎么评估？", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        log = db.scalars(
            select(AgentDecisionLog)
            .where(AgentDecisionLog.user_id == user_id)
            .order_by(AgentDecisionLog.id.desc())
            .limit(1)
        ).first()
        assert log is not None
        state = json.loads(log.state_json)
        decision = json.loads(log.decision_json)

    assert state["candidateTrainingTasks"][0]["weakTag"] == "rag_quality"
    assert state["candidateTrainingTasks"][0]["masteryScore"] == 45
    assert decision["selectedTrainingTask"]["weakTag"] == "rag_quality"
    assert "训练任务" in decision["selectedTrainingTask"]["reason"]
```

- [x] **Step 2: Run failing test**

Run:

```powershell
python -m pytest tests/test_agent_training_tasks.py -q
```

Expected:

```text
Test fails because candidateTrainingTasks and selectedTrainingTask are not in Agent state/decision.
```

- [x] **Step 3: Add training task selector**

Modify `backend_python/training_tasks.py`:

```python
def list_candidate_training_tasks(
    db: Session,
    *,
    user_id: int,
    application_profile_id: int | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    statement = select(TrainingTask).where(
        TrainingTask.user_id == user_id,
        TrainingTask.status.in_({"todo", "in_progress"}),
    )
    if application_profile_id is not None:
        statement = statement.where(
            (TrainingTask.application_profile_id == application_profile_id)
            | (TrainingTask.application_profile_id.is_(None))
        )
    tasks = db.scalars(
        statement.order_by(
            TrainingTask.priority.desc(),
            TrainingTask.mastery_score.asc(),
            TrainingTask.updated_at.desc(),
        ).limit(limit)
    ).all()
    return [serialize_training_task(task) for task in tasks]


def select_agent_training_task(tasks: list[dict[str, Any]], *, agent_mode: str) -> dict[str, Any]:
    for task in tasks:
        mastery = int(task.get("masteryScore") or 0)
        if agent_mode == "coach" and task.get("priority") == "high" and mastery < 60:
            return {**task, "reason": "coach 模式优先补低掌握度高优先级训练任务"}
        if agent_mode == "interview" and mastery < 80:
            return {**task, "reason": "interview 模式检验尚未稳定掌握的训练任务"}
    return {}
```

- [x] **Step 4: Add training tasks into next-question Agent State**

Modify `backend_python/routes/interview.py` near Agent state construction:

```python
from ..training_tasks import list_candidate_training_tasks, select_agent_training_task
```

After current user and application profile are known:

```python
candidate_training_tasks = list_candidate_training_tasks(
    db,
    user_id=current_user.id,
    application_profile_id=payload.applicationProfileId,
    limit=3,
)
selected_training_task = select_agent_training_task(candidate_training_tasks, agent_mode=payload.agentMode)
```

When building `agent_state`:

```python
agent_state["candidateTrainingTasks"] = candidate_training_tasks
```

After `agent_decision` exists:

```python
if selected_training_task:
    agent_decision["selectedTrainingTask"] = {
        "id": selected_training_task.get("id"),
        "weakTag": selected_training_task.get("weakTag"),
        "title": selected_training_task.get("title"),
        "masteryScore": selected_training_task.get("masteryScore"),
        "priority": selected_training_task.get("priority"),
        "reason": selected_training_task.get("reason"),
    }
```

- [x] **Step 5: Run Agent training task test**

Run:

```powershell
python -m pytest tests/test_agent_training_tasks.py tests/test_interview_agent_route.py -q
```

Expected:

```text
All tests pass, existing next-question behavior remains compatible.
```

---

## Task 10: Phase Learning Docs And Progress Updates

**Learning point before coding:** 学习文档是这个项目的“可讲述性资产”。每做完一个工程阶段，都要把为什么这么做、代码在哪、面试怎么讲写清楚。

**Files:**
- Create: `docs/learning/10-用户角色与后台权限MVP怎么设计.md`
- Create: `docs/learning/11-训练任务系统如何承接weakTags.md`
- Create: `docs/learning/12-训练中心前端页面如何拆分.md`
- Create: `docs/learning/13-管理员后台MVP如何设计.md`
- Create: `docs/learning/14-训练任务如何影响Agent决策.md`
- Modify: `docs/pre-deployment-progress.md`

- [x] **Step 1: Create role/admin learning doc**

Write `docs/learning/10-用户角色与后台权限MVP怎么设计.md` with these sections:

```markdown
# 10 用户角色与后台权限 MVP 怎么设计

## 1. 本阶段解决什么问题

## 2. 为什么只做 user/admin 两种角色

## 3. get_current_user 和 require_admin_user 的区别

## 4. 为什么前端隐藏入口不等于权限控制

## 5. 关键代码位置

## 6. 面试时怎么讲

## 7. 当前边界
```

- [x] **Step 2: Create training task learning doc**

Write `docs/learning/11-训练任务系统如何承接weakTags.md` with these sections:

```markdown
# 11 训练任务系统如何承接 weakTags

## 1. weakTags 的局限

## 2. TrainingTask 解决什么问题

## 3. 去重规则为什么重要

## 4. mastery_score 为什么先用规则评分

## 5. 关键代码位置

## 6. 面试时怎么讲

## 7. 当前边界
```

- [x] **Step 3: Create frontend training center learning doc**

Write `docs/learning/12-训练中心前端页面如何拆分.md` with these sections:

```markdown
# 12 训练中心前端页面如何拆分

## 1. 为什么要从单一面试页拆出训练中心

## 2. 原生 JS 如何做轻量状态管理

## 3. 训练任务列表和详情如何协作

## 4. 移动端布局要注意什么

## 5. 关键代码位置

## 6. 面试时怎么讲
```

- [x] **Step 4: Create admin MVP learning doc**

Write `docs/learning/13-管理员后台MVP如何设计.md` with these sections:

```markdown
# 13 管理员后台 MVP 如何设计

## 1. 为什么后台先做只读 MVP

## 2. 后台 summary、用户、知识库、日志分别解决什么问题

## 3. 管理端和用户端权限边界

## 4. 关键代码位置

## 5. 面试时怎么讲

## 6. 后续扩展
```

- [x] **Step 5: Create Agent training task learning doc**

Write `docs/learning/14-训练任务如何影响Agent决策.md` with these sections:

```markdown
# 14 训练任务如何影响 Agent 决策

## 1. 为什么训练任务只作为辅助信号

## 2. candidateTrainingTasks 放在 Agent State 的意义

## 3. selectedTrainingTask 记录什么

## 4. 如何避免 Agent 死磕同一弱点

## 5. 关键代码位置

## 6. 面试时怎么讲
```

- [x] **Step 6: Update progress doc**

Update `docs/pre-deployment-progress.md` with a Productization V2 table:

```markdown
## 产品化 V2 进度

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| 阶段 1：用户角色与后台权限基础 | 已完成 | User.role、require_admin_user、admin summary 已落地。 |
| 阶段 2：训练任务后端 | 已完成 | TrainingTask、训练任务 service、训练任务 API 已落地。 |
| 阶段 3：用户端训练中心 | 已完成阶段性版本 | 训练任务列表、详情、开始/完成/归档交互已落地。 |
| 阶段 4：管理员后台 MVP | 已完成阶段性版本 | 后台入口、summary、用户、文档、RAG 日志、Agent 日志只读视图已落地。 |
| 阶段 5：Agent 读取训练任务 | 已完成阶段性版本 | Agent State 可读取高优先级训练任务并记录 selectedTrainingTask。 |
| 阶段 6：LangGraph 迁移预留 | 待执行 | 等当前阶段测试稳定后写迁移学习文档。 |
```

---

## Task 11: LangGraph Migration Reserve Doc

**Learning point before coding:** 现在不上 LangGraph，不代表不懂 Agent 框架。更好的表达是：先把自研 Agent 的 state、node、edge、trace 稳定下来，再迁移到 LangGraph。

**Files:**
- Create: `docs/learning/15-自研Agent如何迁移到LangGraph.md`

- [x] **Step 1: Write LangGraph migration doc**

Create `docs/learning/15-自研Agent如何迁移到LangGraph.md`:

```markdown
# 15 自研 Agent 如何迁移到 LangGraph

## 1. 为什么本阶段不直接引入 LangGraph

当前训练任务系统、管理员后台和 Agent State 还在演进。直接引入 LangGraph 会放大改动范围，也会让学习重点从 Agent 底层概念转移到框架 API。

## 2. 当前自研 Agent 已经有哪些 LangGraph 雏形

- Agent State。
- ToolCalls。
- nodeTrace。
- observe_state。
- analyze_answer。
- retrieve_context。
- select_weakness_strategy。
- select_training_template。
- select_action。
- generate_question。
- update_memory。

## 3. 映射关系

| 当前自研模块 | LangGraph 概念 |
| --- | --- |
| Agent State dict | Graph State |
| observe_state | node |
| retrieve_context | tool node |
| select_action | decision node |
| nextAction | conditional edge |
| AgentDecisionLog | checkpoint / trace 的过渡形态 |
| nodeTrace | graph execution trace |

## 4. 最小 POC 范围

第一版只迁移：

```text
observe_state -> retrieve_context -> select_action -> generate_question
```

不迁移完整训练闭环。

## 5. 面试时怎么讲

我没有一开始就引入 LangGraph，是因为我先做了自研轻量 Orchestrator，把 Agent State、工具调用、决策、fallback、guardrail 和 nodeTrace 都跑通。这样我能讲清底层逻辑。后续迁移 LangGraph 时，可以把现有节点映射成 StateGraph nodes，把 nextAction 作为 conditional edge，把 checkpoint 用于多轮面试状态恢复。

## 6. 当前边界

当前没有安装 LangGraph 或 LangChain，没有 checkpoint，也没有 human-in-the-loop。它们属于后续 POC。
```

- [x] **Step 2: Check doc has no placeholders**

Run:

```powershell
rg -n "T[O]DO|T[B]D|待[定]|占[位]|F[IX]ME" docs/learning/15-自研Agent如何迁移到LangGraph.md
```

Expected:

```text
No matches.
```

---

## Task 12: Full Verification And Browser Validation

**Files:**
- No required code changes unless verification finds defects.

- [x] **Step 1: Run focused backend tests**

Run:

```powershell
python -m pytest tests/test_admin_auth.py tests/test_admin_routes.py tests/test_training_tasks.py tests/test_training_task_generation.py tests/test_agent_training_tasks.py tests/test_interview_agent_route.py -q
```

Expected:

```text
All focused backend tests pass.
```

- [x] **Step 2: Run full backend tests**

Run:

```powershell
python -m pytest -q
```

Expected:

```text
All backend tests pass.
```

- [x] **Step 3: Run focused frontend tests**

Run:

```powershell
node tests/frontend_training_center.test.mjs
node tests/frontend_admin_permissions.test.mjs
node tests/frontend_admin_dashboard.test.mjs
node tests/frontend_interview_flow.test.mjs
```

Expected:

```text
No assertion failures.
```

- [x] **Step 4: Run all frontend .mjs tests**

Run:

```powershell
Get-ChildItem tests -Filter "*.mjs" | ForEach-Object { node $_.FullName; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Expected:

```text
All frontend .mjs tests pass.
```

- [x] **Step 5: Start or confirm local server**

Run:

```powershell
uvicorn backend_python.main:app --host 127.0.0.1 --port 8000
```

Expected:

```text
Server is reachable at http://localhost:8000/
```

If a server is already running on port 8000, use the existing server instead of starting a duplicate.

- [x] **Step 6: Browser desktop verification**

Use the in-app browser at:

```text
http://localhost:8000/
```

Verify:

- Page opens without console errors.
- Normal user does not see admin entry.
- Training center renders after login.
- Training task list does not show `undefined`.
- Layout does not overflow horizontally at desktop width.

- [x] **Step 7: Browser mobile verification**

Use mobile viewport around 390px width.

Verify:

- Training center stacks vertically.
- Long weakTag/title text wraps.
- Admin dashboard cards wrap.
- No horizontal overflow.

- [x] **Step 8: Update progress with final verification**

Update `docs/pre-deployment-progress.md` with exact command outputs:

```markdown
### 产品化 V2 验证记录

- 后端聚焦测试：`...`，结果：`...`
- 后端全量测试：`...`，结果：`...`
- 前端聚焦测试：`...`，结果：`...`
- 前端全量测试：`...`，结果：`...`
- 浏览器桌面验证：已验证 / 未验证，原因：...
- 浏览器移动端验证：已验证 / 未验证，原因：...
```

---

## Self-Review Checklist

Spec coverage:

- User/admin role foundation: Task 1 and Task 2.
- Training task backend: Task 3 and Task 4.
- User training center: Task 5 and Task 6.
- Admin MVP: Task 7 and Task 8.
- Agent reads training tasks: Task 9.
- LangGraph reserve: Task 11.
- Learning docs and progress: Task 10 and Task 12.
- Verification: Task 12.

Placeholder scan:

- This plan must not contain placeholder markers, unfinished sections, or vague future-work commands.

Type consistency:

- Backend JSON uses camelCase for API responses: `weakTag`, `masteryScore`, `attemptCount`.
- Database model uses snake_case: `weak_tag`, `mastery_score`, `attempt_count`.
- Frontend state uses `session.training` and `session.admin`.
- Admin role is exactly `admin`; normal role is exactly `user`.

