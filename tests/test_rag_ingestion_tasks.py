import json
from uuid import uuid4

from backend_python.database import SessionLocal, init_db
from backend_python.db_models import RagIngestionTask, User
from backend_python.rag_ingestion_tasks import (
    create_ingestion_task,
    fail_ingestion_task,
    mark_ingestion_text_ready,
    serialize_ingestion_task,
    succeed_ingestion_task,
)

init_db()


def create_user(db, prefix: str = "task-user") -> User:
    suffix = uuid4().hex
    user = User(
        email=f"{prefix}-{suffix}@example.com",
        username=f"{prefix}_{suffix[:10]}",
        password_hash="hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_and_serialize_ingestion_task() -> None:
    with SessionLocal() as db:
        user = create_user(db)

        task = create_ingestion_task(
            db,
            user_id=user.id,
            title="FastAPI 知识",
            knowledge_base="role_knowledge",
            original_filename="fastapi.md",
            visibility="private",
            metadata={"positionTag": "python_backend"},
        )

        persisted = db.query(RagIngestionTask).filter_by(task_id=task.task_id).one()
        payload = serialize_ingestion_task(persisted)

    assert payload["taskId"] == task.task_id
    assert payload["status"] == "pending"
    assert payload["progress"] == 0
    assert payload["knowledgeBase"] == "role_knowledge"
    assert payload["originalFilename"] == "fastapi.md"
    assert payload["canRetry"] is False
    assert payload["hasTextSnapshot"] is False


def test_text_ready_failure_can_be_retried() -> None:
    with SessionLocal() as db:
        user = create_user(db)
        task = create_ingestion_task(
            db,
            user_id=user.id,
            title="FastAPI 知识",
            knowledge_base="role_knowledge",
            original_filename="fastapi.md",
            visibility="private",
            metadata={},
        )

        mark_ingestion_text_ready(
            db,
            task,
            text_snapshot="FastAPI Depends 用于依赖注入。",
            preview={"textLength": 24, "chunkCount": 1, "warnings": []},
        )
        fail_ingestion_task(db, task, error_message="document create failed")

        db.refresh(task)
        payload = serialize_ingestion_task(task)
        input_payload = json.loads(task.input_json)

    assert payload["status"] == "failed"
    assert payload["canRetry"] is True
    assert payload["error"] == "document create failed"
    assert payload["preview"]["chunkCount"] == 1
    assert input_payload["textSnapshot"].startswith("FastAPI")


def test_success_task_records_document_result() -> None:
    with SessionLocal() as db:
        user = create_user(db)
        task = create_ingestion_task(
            db,
            user_id=user.id,
            title="FastAPI 知识",
            knowledge_base="role_knowledge",
            original_filename="fastapi.md",
            visibility="private",
            metadata={},
        )

        succeed_ingestion_task(
            db,
            task,
            document_id=12,
            result={"document": {"id": 12}, "preview": {"chunkCount": 1}},
        )

        db.refresh(task)
        payload = serialize_ingestion_task(task)

    assert payload["status"] == "succeeded"
    assert payload["progress"] == 100
    assert payload["documentId"] == 12
    assert payload["result"]["document"]["id"] == 12
    assert payload["canRetry"] is False
