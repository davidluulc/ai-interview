import json
from datetime import UTC, datetime
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
        task.completed_at = datetime.now(UTC)
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


def merge_ingestion_task_input(
    db: Session,
    task: RagIngestionTask,
    values: dict[str, Any],
) -> RagIngestionTask:
    input_payload = json_loads(task.input_json)
    input_payload.update(values)
    task.input_json = json_dumps(input_payload)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


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
    return bool(
        task.status == "failed"
        and task.can_retry
        and payload.get("textSnapshot")
        and task.retry_count < task.max_retries
    )


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
