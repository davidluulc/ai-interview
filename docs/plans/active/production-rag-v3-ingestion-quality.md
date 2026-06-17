# Production RAG V3 Ingestion Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 RAG 文件摄取任务从内存态升级为数据库持久化任务，并补齐失败重试、用户侧任务历史和管理员后台摄取质量监控。

**Architecture:** 新增 `RagIngestionTask` ORM 表和 `rag_ingestion_tasks.py` 服务层，`routes/rag_documents.py` 继续承担用户侧上传与查询接口，`routes/admin.py` 增加管理员只读监控接口。Vue3 知识库页显示用户自己的摄取任务，管理员后台显示全局摄取任务质量摘要。

**Tech Stack:** FastAPI, SQLAlchemy, SQLite local dev, Alembic-style ORM model compatibility, Pytest, Vue3, Pinia, TypeScript, Vitest.

---

## File Structure

- Modify: `backend_python/db_models.py`
  - 增加 `RagIngestionTask` ORM 模型。
  - 给 `User` 增加 `rag_ingestion_tasks` relationship。
- Create: `backend_python/rag_ingestion_tasks.py`
  - 封装任务创建、更新、序列化、重试判断和失败分类。
- Modify: `backend_python/routes/rag_documents.py`
  - 上传接口改为写入持久化任务。
  - 新增用户侧任务列表和 retry 接口。
  - 保持已有 upload response 兼容。
- Modify: `backend_python/routes/admin.py`
  - 新增管理员 RAG 摄取任务监控接口。
- Create: `alembic/versions/20260617_0002_add_rag_ingestion_tasks.py`
  - 创建 `rag_ingestion_tasks` 表和必要索引。
- Test: `tests/test_rag_ingestion_tasks.py`
  - 服务层持久化和重试规则。
- Modify: `tests/test_rag_documents_upload_route.py`
  - 上传接口兼容、任务查询、任务列表、retry 权限。
- Modify: `tests/test_admin_rag_quality.py` or create `tests/test_admin_rag_ingestion_tasks.py`
  - 管理员任务监控接口。
- Modify: `frontend/src/api/knowledge.ts`
  - 增加 ingestion task list / retry API。
- Modify: `frontend/src/stores/knowledge.ts`
  - 增加任务历史状态、加载和 retry action。
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
  - 展示最近导入任务、失败原因和 retry 按钮。
- Modify: `frontend/src/api/admin.ts`
  - 增加管理员摄取任务类型和 API。
- Modify: `frontend/src/stores/admin.ts`
  - 加载管理员摄取任务。
- Modify: `frontend/src/pages/app/AdminPage.vue`
  - 增加 RAG 摄取任务监控区块。
- Modify tests:
  - `frontend/src/api/knowledge.test.ts`
  - `frontend/src/stores/knowledge.test.ts`
  - `frontend/src/pages/app/knowledge-page.test.ts`
  - `frontend/src/api/admin.test.ts` if present, otherwise `frontend/src/stores/admin.test.ts`
  - `frontend/src/pages/app/admin-page.test.ts`

---

### Task 1: Backend Persistent Task Model And Service

**Files:**
- Modify: `backend_python/db_models.py`
- Create: `alembic/versions/20260617_0002_add_rag_ingestion_tasks.py`
- Create: `backend_python/rag_ingestion_tasks.py`
- Test: `tests/test_rag_ingestion_tasks.py`

- [ ] **Step 1: Write failing service tests**

Add `tests/test_rag_ingestion_tasks.py`:

```python
import json

from backend_python.db_models import RagIngestionTask, User
from backend_python.rag_ingestion_tasks import (
    create_ingestion_task,
    fail_ingestion_task,
    mark_ingestion_text_ready,
    serialize_ingestion_task,
    succeed_ingestion_task,
)


def create_user(db, email="task-user@example.com"):
    user = User(email=email, username=email.split("@")[0], password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_and_serialize_ingestion_task(db_session):
    user = create_user(db_session)

    task = create_ingestion_task(
        db_session,
        user_id=user.id,
        title="FastAPI 知识",
        knowledge_base="role",
        original_filename="fastapi.md",
        visibility="private",
        metadata={"positionTag": "python_backend"},
    )

    persisted = db_session.query(RagIngestionTask).filter_by(task_id=task.task_id).one()
    payload = serialize_ingestion_task(persisted)

    assert payload["taskId"] == task.task_id
    assert payload["status"] == "pending"
    assert payload["progress"] == 0
    assert payload["knowledgeBase"] == "role"
    assert payload["originalFilename"] == "fastapi.md"
    assert payload["canRetry"] is False


def test_text_ready_failure_can_be_retried(db_session):
    user = create_user(db_session)
    task = create_ingestion_task(
        db_session,
        user_id=user.id,
        title="FastAPI 知识",
        knowledge_base="role",
        original_filename="fastapi.md",
        visibility="private",
        metadata={},
    )

    mark_ingestion_text_ready(
        db_session,
        task,
        text_snapshot="FastAPI Depends 用于依赖注入。",
        preview={"textLength": 24, "chunkCount": 1, "warnings": []},
    )
    fail_ingestion_task(db_session, task, error_message="document create failed")

    db_session.refresh(task)
    payload = serialize_ingestion_task(task)

    assert payload["status"] == "failed"
    assert payload["canRetry"] is True
    assert payload["error"] == "document create failed"
    assert json.loads(task.input_json)["textSnapshot"].startswith("FastAPI")


def test_success_task_records_document_result(db_session):
    user = create_user(db_session)
    task = create_ingestion_task(
        db_session,
        user_id=user.id,
        title="FastAPI 知识",
        knowledge_base="role",
        original_filename="fastapi.md",
        visibility="private",
        metadata={},
    )

    succeed_ingestion_task(
        db_session,
        task,
        document_id=12,
        result={"document": {"id": 12}, "preview": {"chunkCount": 1}},
    )

    db_session.refresh(task)
    payload = serialize_ingestion_task(task)

    assert payload["status"] == "succeeded"
    assert payload["progress"] == 100
    assert payload["documentId"] == 12
    assert payload["result"]["document"]["id"] == 12
```

- [ ] **Step 2: Run service test and verify it fails**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_tasks.py -q
```

Expected: FAIL because `RagIngestionTask` and `backend_python.rag_ingestion_tasks` do not exist yet.

- [ ] **Step 3: Add ORM model**

Modify `backend_python/db_models.py`:

```python
class User(Base):
    # existing fields...
    rag_ingestion_tasks: Mapped[list["RagIngestionTask"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RagIngestionTask(Base):
    __tablename__ = "rag_ingestion_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("rag_documents.id"), nullable=True, index=True)
    knowledge_base: Mapped[str] = mapped_column(String(50), default="", index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    source_extension: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(255), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    can_retry: Mapped[int] = mapped_column(Integer, default=0, index=True)
    preview_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user: Mapped[User] = relationship(back_populates="rag_ingestion_tasks")
```

- [ ] **Step 4: Add service implementation**

Create `backend_python/rag_ingestion_tasks.py`:

```python
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from .db_models import RagIngestionTask

VALID_TASK_STATUSES = {"pending", "running", "succeeded", "failed"}


def json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def json_loads(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def create_ingestion_task(
    db: Session,
    *,
    user_id: int,
    title: str,
    knowledge_base: str,
    original_filename: str,
    visibility: str,
    metadata: dict[str, Any],
) -> RagIngestionTask:
    filename = str(original_filename or "")
    task = RagIngestionTask(
        task_id=f"rag_ingestion-{uuid4().hex}",
        user_id=user_id,
        title=str(title or "").strip(),
        knowledge_base=str(knowledge_base or ""),
        original_filename=filename,
        source_extension=Path(filename).suffix.lower(),
        status="pending",
        progress=0,
        message="RAG document ingestion task created.",
        input_json=json_dumps(
            {
                "title": str(title or "").strip(),
                "knowledgeBase": str(knowledge_base or ""),
                "visibility": str(visibility or "private"),
                "metadata": metadata or {},
                "originalFilename": filename,
            }
        ),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_ingestion_task(
    db: Session,
    task: RagIngestionTask,
    *,
    status: str,
    progress: int,
    message: str = "",
    error_message: str = "",
) -> RagIngestionTask:
    if status not in VALID_TASK_STATUSES:
        raise ValueError(f"Invalid ingestion task status: {status}")
    task.status = status
    task.progress = max(0, min(int(progress), 100))
    if message:
        task.message = message
    task.error_message = error_message
    if status in {"succeeded", "failed"}:
        task.completed_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def mark_ingestion_text_ready(
    db: Session,
    task: RagIngestionTask,
    *,
    text_snapshot: str,
    preview: dict[str, Any],
) -> RagIngestionTask:
    input_payload = json_loads(task.input_json)
    input_payload["textSnapshot"] = text_snapshot
    task.input_json = json_dumps(input_payload)
    task.preview_json = json_dumps(preview)
    task.can_retry = 1
    return update_ingestion_task(db, task, status="running", progress=60, message="Creating RAG document.")


def fail_ingestion_task(db: Session, task: RagIngestionTask, *, error_message: str) -> RagIngestionTask:
    return update_ingestion_task(
        db,
        task,
        status="failed",
        progress=100,
        message="RAG document ingestion failed.",
        error_message=error_message,
    )


def succeed_ingestion_task(
    db: Session,
    task: RagIngestionTask,
    *,
    document_id: int,
    result: dict[str, Any],
) -> RagIngestionTask:
    task.document_id = document_id
    task.result_json = json_dumps(result)
    task.can_retry = 0
    return update_ingestion_task(db, task, status="succeeded", progress=100, message="RAG document ingestion finished.")


def can_retry_ingestion_task(task: RagIngestionTask) -> bool:
    payload = json_loads(task.input_json)
    return bool(task.status == "failed" and task.can_retry and payload.get("textSnapshot") and task.retry_count < task.max_retries)


def serialize_ingestion_task(task: RagIngestionTask) -> dict[str, Any]:
    preview = json_loads(task.preview_json)
    result = json_loads(task.result_json)
    input_payload = json_loads(task.input_json)
    return {
        "id": task.id,
        "taskId": task.task_id,
        "userId": task.user_id,
        "documentId": task.document_id,
        "knowledgeBase": task.knowledge_base,
        "title": task.title,
        "originalFilename": task.original_filename,
        "sourceExtension": task.source_extension,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "error": task.error_message,
        "retryCount": task.retry_count,
        "maxRetries": task.max_retries,
        "canRetry": can_retry_ingestion_task(task),
        "preview": preview,
        "result": result,
        "document": result.get("document") if isinstance(result.get("document"), dict) else None,
        "createdAt": task.created_at.isoformat() if task.created_at else None,
        "updatedAt": task.updated_at.isoformat() if task.updated_at else None,
        "completedAt": task.completed_at.isoformat() if task.completed_at else None,
        "hasTextSnapshot": bool(input_payload.get("textSnapshot")),
    }
```

- [ ] **Step 5: Run service tests**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_tasks.py -q
```

Expected: PASS.

- [ ] **Step 6: Add Alembic migration**

Create `alembic/versions/20260617_0002_add_rag_ingestion_tasks.py`:

```python
"""add rag ingestion tasks

Revision ID: 20260617_0002
Revises: 20260614_0001
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260617_0002"
down_revision = "20260614_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_ingestion_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("knowledge_base", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("original_filename", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("source_extension", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("can_retry", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("preview_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("input_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["rag_documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rag_ingestion_tasks_id"), "rag_ingestion_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_task_id"), "rag_ingestion_tasks", ["task_id"], unique=True)
    op.create_index(op.f("ix_rag_ingestion_tasks_user_id"), "rag_ingestion_tasks", ["user_id"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_document_id"), "rag_ingestion_tasks", ["document_id"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_status"), "rag_ingestion_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_can_retry"), "rag_ingestion_tasks", ["can_retry"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_knowledge_base"), "rag_ingestion_tasks", ["knowledge_base"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_ingestion_tasks_knowledge_base"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_can_retry"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_status"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_document_id"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_user_id"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_task_id"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_id"), table_name="rag_ingestion_tasks")
    op.drop_table("rag_ingestion_tasks")
```

---

### Task 2: User Upload Route Persistence And Retry

**Files:**
- Modify: `backend_python/routes/rag_documents.py`
- Modify: `tests/test_rag_documents_upload_route.py`

- [ ] **Step 1: Add failing route tests**

Append route tests covering:

```python
def test_upload_persists_ingestion_task(client, auth_headers):
    files = {"file": ("fastapi.md", b"# FastAPI\n\nDepends is dependency injection.", "text/markdown")}
    data = {"title": "FastAPI", "knowledgeBase": "role", "visibility": "private", "metadata": "{}"}

    response = client.post("/api/rag/documents/upload", data=data, files=files, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    task_id = body["taskId"]

    detail = client.get(f"/api/rag/documents/ingestion-tasks/{task_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "succeeded"
    assert detail.json()["document"]["id"] == body["document"]["id"]


def test_list_ingestion_tasks_returns_current_user_tasks(client, auth_headers):
    response = client.get("/api/rag/documents/ingestion-tasks", headers=auth_headers)

    assert response.status_code == 200
    assert "items" in response.json()


def test_retry_non_retryable_task_returns_409(client, auth_headers):
    files = {"file": ("bad.exe", b"not supported", "application/octet-stream")}
    data = {"title": "Bad", "knowledgeBase": "role", "visibility": "private", "metadata": "{}"}

    response = client.post("/api/rag/documents/upload", data=data, files=files, headers=auth_headers)

    assert response.status_code == 400
    task_list = client.get("/api/rag/documents/ingestion-tasks", headers=auth_headers).json()["items"]
    failed_task = task_list[0]

    retry = client.post(f"/api/rag/documents/ingestion-tasks/{failed_task['taskId']}/retry", headers=auth_headers)
    assert retry.status_code == 409
```

Adapt fixture names to the existing test file if they differ.

- [ ] **Step 2: Run route tests and verify failure**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py -q
```

Expected: FAIL because routes still use memory task status and do not expose list / retry.

- [ ] **Step 3: Replace memory ingestion task usage in upload route**

In `backend_python/routes/rag_documents.py`, import the new service:

```python
from ..db_models import RagChunk, RagDocument, RagIngestionTask, User
from ..rag_ingestion_tasks import (
    can_retry_ingestion_task,
    create_ingestion_task,
    fail_ingestion_task,
    json_loads,
    mark_ingestion_text_ready,
    serialize_ingestion_task,
    succeed_ingestion_task,
    update_ingestion_task,
)
```

Remove `task_status` imports for ingestion usage.

In `upload_document()`, create and update persistent task:

```python
parsed_metadata = json.loads(metadata or "{}")
if not isinstance(parsed_metadata, dict):
    parsed_metadata = {}
task = create_ingestion_task(
    db,
    user_id=current_user.id,
    title=title,
    knowledge_base=validate_knowledge_base(knowledgeBase),
    original_filename=file.filename or title,
    visibility=normalize_document_visibility(visibility),
    metadata=parsed_metadata,
)
try:
    update_ingestion_task(db, task, status="running", progress=20, message="Parsing uploaded file.")
    content = await file.read()
    text = await extract_text_from_upload(filename=file.filename or title, content=content)
    preview = build_ingestion_preview(text, title=title)
    mark_ingestion_text_ready(db, task, text_snapshot=text, preview=preview)
    document = await create_rag_document_with_embeddings(...)
    result = {"document": serialize_document(document), "preview": preview}
    succeed_ingestion_task(db, task, document_id=document.id, result=result)
    return {"taskId": task.task_id, "status": "success", **result}
except (IngestionError, json.JSONDecodeError) as exc:
    fail_ingestion_task(db, task, error_message=str(exc))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
```

Keep the final response shape compatible with the current frontend: `taskId`, `status`, `document`, `preview`.

- [ ] **Step 4: Add list/detail/retry routes**

Add before `@router.get("/{document_id}")`:

```python
@router.get("/ingestion-tasks")
async def list_ingestion_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, Any]]]:
    tasks = db.scalars(
        select(RagIngestionTask)
        .where(RagIngestionTask.user_id == current_user.id)
        .order_by(RagIngestionTask.updated_at.desc(), RagIngestionTask.id.desc())
        .limit(30)
    ).all()
    return {"items": [serialize_ingestion_task(task) for task in tasks]}
```

Update detail route to read from DB and enforce owner:

```python
@router.get("/ingestion-tasks/{task_id}")
async def get_ingestion_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    task = db.scalar(
        select(RagIngestionTask).where(
            RagIngestionTask.task_id == task_id,
            RagIngestionTask.user_id == current_user.id,
        )
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG ingestion task not found")
    return serialize_ingestion_task(task)
```

Add retry route:

```python
@router.post("/ingestion-tasks/{task_id}/retry")
async def retry_ingestion_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    task = db.scalar(
        select(RagIngestionTask).where(
            RagIngestionTask.task_id == task_id,
            RagIngestionTask.user_id == current_user.id,
        )
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG ingestion task not found")
    if not can_retry_ingestion_task(task):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This ingestion task cannot be retried. Upload the file again.")

    payload = json_loads(task.input_json)
    task.retry_count += 1
    update_ingestion_task(db, task, status="running", progress=60, message="Retrying RAG document ingestion.")
    preview = json_loads(task.preview_json)
    document = await create_rag_document_with_embeddings(
        db,
        user_id=current_user.id,
        title=payload.get("title") or task.title,
        knowledge_base=validate_knowledge_base(payload.get("knowledgeBase") or task.knowledge_base),
        source_type="upload_retry",
        content=payload.get("textSnapshot") or "",
        metadata={**(payload.get("metadata") or {}), "retryOfIngestionTaskId": task.task_id},
        visibility=normalize_document_visibility(payload.get("visibility") or "private"),
    )
    result = {"document": serialize_document(document), "preview": preview}
    succeed_ingestion_task(db, task, document_id=document.id, result=result)
    return serialize_ingestion_task(task)
```

- [ ] **Step 5: Run route tests**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_tasks.py tests/test_rag_documents_upload_route.py -q
```

Expected: PASS.

---

### Task 3: Admin Ingestion Quality Endpoint

**Files:**
- Modify: `backend_python/routes/admin.py`
- Test: `tests/test_admin_rag_ingestion_tasks.py`

- [ ] **Step 1: Write failing admin tests**

Create `tests/test_admin_rag_ingestion_tasks.py`:

```python
from backend_python.db_models import RagIngestionTask, User


def test_admin_lists_rag_ingestion_tasks(db_session, admin_client):
    user = User(email="ingest-owner@example.com", username="ingest-owner", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    task = RagIngestionTask(
        task_id="rag_ingestion-admin-visible",
        user_id=user.id,
        title="Broken upload",
        knowledge_base="role",
        original_filename="broken.md",
        status="failed",
        progress=100,
        error_message="Parsed empty text from uploaded file.",
        can_retry=0,
    )
    db_session.add(task)
    db_session.commit()

    response = admin_client.get("/api/admin/rag/ingestion-tasks")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["failedCount"] >= 1
    assert body["items"][0]["taskId"] == "rag_ingestion-admin-visible"
    assert body["items"][0]["userEmail"] == "ingest-owner@example.com"
```

Adapt `admin_client` fixture name to existing admin tests.

- [ ] **Step 2: Run admin test and verify failure**

Run:

```powershell
python -m pytest tests/test_admin_rag_ingestion_tasks.py -q
```

Expected: FAIL because endpoint does not exist.

- [ ] **Step 3: Implement admin endpoint**

Modify `backend_python/routes/admin.py`:

```python
from ..db_models import AgentDecisionLog, InterviewRecord, RagDocument, RagIngestionTask, RagRetrievalLog, User
from ..rag_ingestion_tasks import serialize_ingestion_task
```

Add helper:

```python
def build_ingestion_task_quality_payload(tasks: list[RagIngestionTask]) -> dict[str, Any]:
    summary = {
        "totalCount": len(tasks),
        "runningCount": 0,
        "succeededCount": 0,
        "failedCount": 0,
        "retryableCount": 0,
    }
    items = []
    for task in tasks:
        item = serialize_ingestion_task(task)
        item["userEmail"] = task.user.email if task.user else ""
        status_value = item.get("status")
        if status_value == "running":
            summary["runningCount"] += 1
        elif status_value == "succeeded":
            summary["succeededCount"] += 1
        elif status_value == "failed":
            summary["failedCount"] += 1
        if item.get("canRetry"):
            summary["retryableCount"] += 1
        items.append(item)
    return {"summary": summary, "items": items}
```

Add route:

```python
@router.get("/rag/ingestion-tasks")
async def admin_rag_ingestion_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> dict[str, Any]:
    tasks = db.scalars(
        select(RagIngestionTask)
        .order_by(RagIngestionTask.updated_at.desc(), RagIngestionTask.id.desc())
        .limit(bounded_limit(limit))
    ).all()
    return build_ingestion_task_quality_payload(list(tasks))
```

- [ ] **Step 4: Run admin tests**

Run:

```powershell
python -m pytest tests/test_admin_rag_ingestion_tasks.py tests/test_admin_rag_quality.py -q
```

Expected: PASS.

---

### Task 4: Frontend Knowledge Page Task History

**Files:**
- Modify: `frontend/src/api/knowledge.ts`
- Modify: `frontend/src/stores/knowledge.ts`
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
- Modify tests:
  - `frontend/src/api/knowledge.test.ts`
  - `frontend/src/stores/knowledge.test.ts`
  - `frontend/src/pages/app/knowledge-page.test.ts`

- [ ] **Step 1: Add failing frontend API/store/page tests**

Extend API tests to assert:

```ts
await getIngestionTasks();
expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/rag/documents/ingestion-tasks"), expect.any(Object));

await retryIngestionTask("rag_ingestion-1");
expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/rag/documents/ingestion-tasks/rag_ingestion-1/retry"), expect.objectContaining({ method: "POST" }));
```

Extend store tests to assert `loadIngestionTasks()` fills `ingestionTasks` and `retryTask()` refreshes the selected task.

Extend page tests to assert failed task error text and retry button render.

- [ ] **Step 2: Run frontend focused tests and verify failure**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts src/pages/app/knowledge-page.test.ts
```

Expected: FAIL because API/store/page do not expose task history and retry yet.

- [ ] **Step 3: Add API methods**

Modify `frontend/src/api/knowledge.ts`:

```ts
export interface RagIngestionTaskListResponse {
  items: RagIngestionTask[];
}

export function getIngestionTasks(): Promise<RagIngestionTaskListResponse> {
  return apiRequest<RagIngestionTaskListResponse>("/api/rag/documents/ingestion-tasks");
}

export function retryIngestionTask(taskId: string): Promise<RagIngestionTask> {
  return apiRequest<RagIngestionTask>(`/api/rag/documents/ingestion-tasks/${encodeURIComponent(taskId)}/retry`, {
    method: "POST"
  });
}
```

- [ ] **Step 4: Add Pinia state/actions**

Modify `frontend/src/stores/knowledge.ts`:

```ts
const ingestionTasks = ref<knowledgeApi.RagIngestionTask[]>([]);
const ingestionTasksLoading = ref(false);
const retryingTaskId = ref("");

async function loadIngestionTasks(): Promise<void> {
  ingestionTasksLoading.value = true;
  try {
    const result = await knowledgeApi.getIngestionTasks();
    ingestionTasks.value = result.items;
  } finally {
    ingestionTasksLoading.value = false;
  }
}

async function retryTask(taskId: string): Promise<void> {
  retryingTaskId.value = taskId;
  uploadError.value = "";
  try {
    ingestionTask.value = await knowledgeApi.retryIngestionTask(taskId);
    await Promise.all([loadIngestionTasks(), loadDocuments()]);
  } catch (err) {
    uploadError.value = err instanceof Error ? err.message : "摄取任务重试失败";
  } finally {
    retryingTaskId.value = "";
  }
}
```

Return the new state/actions.

- [ ] **Step 5: Render task history in KnowledgePage**

Add a compact section below upload result:

```vue
<section class="knowledge-section">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Ingestion Tasks</p>
      <h2>最近导入任务</h2>
    </div>
    <button class="ghost-button" type="button" @click="knowledge.loadIngestionTasks()">刷新</button>
  </div>
  <div v-if="knowledge.ingestionTasks.length" class="ingestion-task-list">
    <article v-for="task in knowledge.ingestionTasks" :key="task.taskId" class="ingestion-task-row">
      <div>
        <strong>{{ task.title || task.originalFilename }}</strong>
        <span>{{ task.knowledgeBase }} · {{ task.status }} · 重试 {{ task.retryCount || 0 }}/{{ task.maxRetries || 0 }}</span>
        <small v-if="task.error">{{ task.error }}</small>
      </div>
      <button
        v-if="task.canRetry"
        class="secondary-button"
        type="button"
        :disabled="knowledge.retryingTaskId === task.taskId"
        @click="knowledge.retryTask(task.taskId)"
      >
        重试
      </button>
    </article>
  </div>
  <p v-else class="empty-state">还没有文件导入任务。</p>
</section>
```

Call `knowledge.loadIngestionTasks()` when the page loads, alongside existing document loading.

- [ ] **Step 6: Run focused frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts src/pages/app/knowledge-page.test.ts
```

Expected: PASS.

---

### Task 5: Frontend Admin Ingestion Monitor

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify tests:
  - `frontend/src/stores/admin.test.ts`
  - `frontend/src/pages/app/admin-page.test.ts`

- [ ] **Step 1: Add failing admin frontend tests**

Add tests expecting:

```ts
expect(screen.getByText("RAG 摄取任务监控")).toBeInTheDocument();
expect(screen.getByText("失败任务")).toBeInTheDocument();
expect(screen.getByText("Parsed empty text from uploaded file.")).toBeInTheDocument();
```

- [ ] **Step 2: Run admin page tests and verify failure**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected: FAIL because admin ingestion monitor does not exist.

- [ ] **Step 3: Add admin API types and method**

Modify `frontend/src/api/admin.ts`:

```ts
export interface AdminRagIngestionTaskSummary {
  totalCount: number;
  runningCount: number;
  succeededCount: number;
  failedCount: number;
  retryableCount: number;
}

export interface AdminRagIngestionTask {
  taskId: string;
  userEmail?: string;
  title: string;
  originalFilename: string;
  knowledgeBase: string;
  status: string;
  error?: string;
  retryCount?: number;
  maxRetries?: number;
  canRetry?: boolean;
  updatedAt?: string | null;
}

export interface AdminRagIngestionTasks {
  summary: AdminRagIngestionTaskSummary;
  items: AdminRagIngestionTask[];
}

export function fetchAdminRagIngestionTasks(): Promise<AdminRagIngestionTasks> {
  return apiRequest<AdminRagIngestionTasks>("/api/admin/rag/ingestion-tasks");
}
```

- [ ] **Step 4: Load admin ingestion tasks in store**

Modify `frontend/src/stores/admin.ts`:

```ts
const ragIngestionTasks = ref<adminApi.AdminRagIngestionTasks | null>(null);

const [summaryResult, usersResult, documentsResult, qualityResult, ingestionResult, logsResult, aiDebugResult, configResult] =
  await Promise.all([
    adminApi.fetchAdminSummary(),
    adminApi.fetchAdminUsers(),
    adminApi.fetchAdminRagDocuments(),
    adminApi.fetchAdminRagQuality(),
    adminApi.fetchAdminRagIngestionTasks(),
    adminApi.fetchAdminAgentLogs(),
    adminApi.fetchAdminAiDebugRecent(),
    adminApi.fetchAdminConfig()
  ]);

ragIngestionTasks.value = ingestionResult;
```

Return `ragIngestionTasks`.

- [ ] **Step 5: Render admin monitor**

Modify `frontend/src/pages/app/AdminPage.vue` to add a readable section near existing RAG quality panels:

```vue
<section class="admin-section">
  <div class="section-heading">
    <div>
      <p class="eyebrow">RAG Ingestion</p>
      <h2>RAG 摄取任务监控</h2>
    </div>
  </div>
  <div v-if="admin.ragIngestionTasks" class="metric-grid">
    <article class="metric-card">
      <span>总任务</span>
      <strong>{{ admin.ragIngestionTasks.summary.totalCount }}</strong>
    </article>
    <article class="metric-card warning">
      <span>失败任务</span>
      <strong>{{ admin.ragIngestionTasks.summary.failedCount }}</strong>
    </article>
    <article class="metric-card">
      <span>可重试</span>
      <strong>{{ admin.ragIngestionTasks.summary.retryableCount }}</strong>
    </article>
  </div>
  <div v-if="admin.ragIngestionTasks?.items.length" class="admin-table">
    <div v-for="task in admin.ragIngestionTasks.items" :key="task.taskId" class="admin-table-row">
      <span>{{ task.originalFilename || task.title }}</span>
      <span>{{ task.userEmail || "未知用户" }}</span>
      <span>{{ task.knowledgeBase }}</span>
      <span>{{ task.status }}</span>
      <small>{{ task.error || "无错误" }}</small>
    </div>
  </div>
  <p v-else class="empty-state">暂无 RAG 摄取任务。</p>
</section>
```

- [ ] **Step 6: Run admin frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected: PASS.

---

### Task 6: Docs, Verification, And Completion

**Files:**
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Move after completion:
  - `docs/specs/active/production-rag-v3-ingestion-quality-design.md` -> `docs/specs/completed/production-rag-v3-ingestion-quality-design.md`
  - `docs/plans/active/production-rag-v3-ingestion-quality.md` -> `docs/plans/completed/production-rag-v3-ingestion-quality.md`

- [ ] **Step 1: Run backend focused tests**

Run:

```powershell
python -m pytest tests/test_rag_ingestion_tasks.py tests/test_rag_documents_upload_route.py tests/test_admin_rag_ingestion_tasks.py -q
```

Expected: PASS.

- [ ] **Step 2: Run backend full tests**

Run:

```powershell
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend focused tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts src/pages/app/knowledge-page.test.ts src/stores/admin.test.ts src/pages/app/admin-page.test.ts
```

Expected: PASS.

- [ ] **Step 4: Run frontend full tests and build**

Run:

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 5: Browser verification**

Verify in the in-app browser:

```text
http://127.0.0.1:5173/vue/app/knowledge
http://127.0.0.1:5173/vue/app/admin
```

Expected:

- 知识库页显示最近导入任务。
- 上传成功后任务状态为 succeeded。
- 失败任务能显示错误原因。
- 管理员后台显示 RAG 摄取任务监控。
- 桌面端和移动端无横向溢出。
- 页面没有 `undefined`。

- [ ] **Step 6: Update docs and archive active files**

Update status docs to say Production RAG V3 is complete. Move this spec and plan to completed. Include exact verification results.

- [ ] **Step 7: Commit**

Run:

```powershell
git status --short
git add backend_python tests frontend docs alembic
git commit -m "feat: persist rag ingestion tasks"
```

Expected: commit succeeds.

---

## Self-Review Checklist

- Spec coverage: this plan covers persistence, retry, user task history, admin monitoring, frontend display, tests, docs and verification.
- 占位检查：plan 中不保留未定稿、待补全、以后再填一类表述。
- Compatibility: `/api/rag/documents/upload` keeps returning `taskId`, `status`, `document`, and `preview`.
- Scope control: OCR, Word/Excel/web parsing, Qdrant/pgvector, real Redis/Celery worker and deployment are explicitly excluded.
