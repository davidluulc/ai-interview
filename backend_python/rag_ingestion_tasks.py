import json
import asyncio
import hashlib
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from .database import SessionLocal
from .db_models import RagIngestionTask

VALID_TASK_STATUSES = {"pending", "queued", "running", "succeeded", "failed"}


def run_async_ingestion(coroutine: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)

    result: dict[str, Any] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(coroutine)
        except Exception as exc:  # pragma: no cover - re-raised in caller thread.
            result["error"] = exc

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


def json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def json_loads(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def get_ingestion_task_by_task_id(db: Session, task_id: str) -> RagIngestionTask | None:
    return db.query(RagIngestionTask).filter_by(task_id=str(task_id or "")).one_or_none()


def build_ingestion_idempotency_key(*, user_id: int, knowledge_base: str, title: str, content_hash: str) -> str:
    raw = f"{user_id}:{knowledge_base}:{str(title or '').strip().lower()}:{content_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def find_ingestion_task_by_idempotency_key(
    db: Session,
    *,
    user_id: int,
    idempotency_key: str,
) -> RagIngestionTask | None:
    tasks = (
        db.query(RagIngestionTask)
        .filter(RagIngestionTask.user_id == user_id)
        .order_by(RagIngestionTask.updated_at.desc(), RagIngestionTask.id.desc())
        .limit(50)
        .all()
    )
    for task in tasks:
        if json_loads(task.result_json).get("idempotencyKey") == idempotency_key:
            return task
    return None


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


def queue_ingestion_task(db: Session, task: RagIngestionTask) -> RagIngestionTask:
    return update_ingestion_task(db, task, status="queued", progress=max(task.progress, 5), message="RAG ingestion task queued.")


def merge_ingestion_task_result(
    db: Session,
    task: RagIngestionTask,
    values: dict[str, Any],
) -> RagIngestionTask:
    result_payload = json_loads(task.result_json)
    result_payload.update(values)
    task.result_json = json_dumps(result_payload)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def dispatch_rag_ingestion_task(db: Session, task: RagIngestionTask) -> RagIngestionTask:
    from .tasks.rag_ingestion import run_rag_ingestion_task

    queue_ingestion_task(db, task)
    try:
        async_result = run_rag_ingestion_task.delay(task.task_id)
        is_eager = bool(getattr(run_rag_ingestion_task.app.conf, "task_always_eager", False))
        db.refresh(task)
        return merge_ingestion_task_result(
            db,
            task,
            {
                "dispatchMode": "eager" if is_eager else "worker",
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


def execute_rag_ingestion_task(task_id: str) -> dict[str, Any]:
    from .rag_store import create_rag_document_with_embeddings, normalize_document_visibility, serialize_document

    with SessionLocal() as db:
        task = get_ingestion_task_by_task_id(db, task_id)
        if task is None:
            return {"taskId": task_id, "status": "failed", "error": "RAG ingestion task not found."}

        started_at = datetime.now(UTC)
        try:
            merge_ingestion_task_result(db, task, {"startedAt": started_at.isoformat()})
            update_ingestion_task(db, task, status="running", progress=max(task.progress, 10), message="Running RAG ingestion task.")
            payload = json_loads(task.input_json)
            text_snapshot = str(payload.get("textSnapshot") or "").strip()
            if not text_snapshot:
                raise ValueError("RAG ingestion task is missing textSnapshot.")

            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            document = run_async_ingestion(
                create_rag_document_with_embeddings(
                    db,
                    user_id=task.user_id,
                    title=str(payload.get("title") or task.title),
                    knowledge_base=str(payload.get("knowledgeBase") or task.knowledge_base),
                    source_type="upload_retry" if task.retry_count else "upload",
                    content=text_snapshot,
                    metadata={
                        **metadata,
                        "originalFilename": task.original_filename,
                        "ingestionTaskId": task.task_id,
                    },
                    visibility=normalize_document_visibility(str(payload.get("visibility") or "private")),
                )
            )
            preview = json_loads(task.preview_json)
            duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            result = {
                **json_loads(task.result_json),
                "document": serialize_document(document),
                "preview": preview,
                "durationMs": duration_ms,
            }
            succeed_ingestion_task(db, task, document_id=document.id, result=result)
        except Exception as exc:
            task.can_retry = 1 if json_loads(task.input_json).get("textSnapshot") else 0
            merge_ingestion_task_result(
                db,
                task,
                {
                    "startedAt": started_at.isoformat(),
                    "durationMs": int((datetime.now(UTC) - started_at).total_seconds() * 1000),
                    "failureStage": "execute",
                },
            )
            fail_ingestion_task(db, task, error_message=str(exc))

        db.refresh(task)
        return serialize_ingestion_task(task)


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
        "dispatchMode": result.get("dispatchMode", ""),
        "celeryTaskId": result.get("celeryTaskId", ""),
        "queuedAt": result.get("queuedAt"),
        "startedAt": result.get("startedAt"),
        "durationMs": result.get("durationMs"),
        "idempotencyKey": result.get("idempotencyKey", ""),
        "idempotencyHit": bool(result.get("idempotencyHit", False)),
        "retryLockedAt": result.get("retryLockedAt"),
        "createdAt": task.created_at.isoformat() if task.created_at else None,
        "updatedAt": task.updated_at.isoformat() if task.updated_at else None,
        "completedAt": task.completed_at.isoformat() if task.completed_at else None,
        "hasTextSnapshot": bool(input_payload.get("textSnapshot")),
    }
