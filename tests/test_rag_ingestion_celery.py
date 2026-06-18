import json

from sqlalchemy import select

from backend_python.database import SessionLocal, init_db
from backend_python.db_models import RagDocument, RagIngestionTask
from backend_python.rag_ingestion_tasks import (
    create_ingestion_task,
    dispatch_rag_ingestion_task,
    execute_rag_ingestion_task,
    merge_ingestion_task_input,
    serialize_ingestion_task,
)
from backend_python.tasks.rag_ingestion import run_rag_ingestion_task
from tests.test_rag_ingestion_tasks import create_user

init_db()


def test_execute_rag_ingestion_task_reads_snapshot_and_writes_success(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_user(db, "celery-ingestion")
        task = create_ingestion_task(
            db,
            user_id=user.id,
            title="Celery RAG",
            knowledge_base="role_knowledge",
            original_filename="celery.md",
            visibility="private",
            metadata={"positionTag": "python_backend"},
        )
        merge_ingestion_task_input(
            db,
            task,
            {
                "textSnapshot": "Celery should build RAG documents from task snapshots.",
                "metadata": {"positionTag": "python_backend"},
            },
        )
        task_id = task.task_id

    result = execute_rag_ingestion_task(task_id)

    assert result["taskId"] == task_id
    assert result["status"] == "succeeded"
    assert result["progress"] == 100
    assert result["documentId"]
    assert result["result"]["document"]["title"] == "Celery RAG"

    with SessionLocal() as db:
        persisted = db.scalar(select(RagIngestionTask).where(RagIngestionTask.task_id == task_id))
        assert persisted is not None
        assert persisted.status == "succeeded"
        assert persisted.progress == 100
        assert persisted.document_id is not None
        document = db.get(RagDocument, persisted.document_id)
        assert document is not None
        assert document.source_type == "upload"
        assert json.loads(document.metadata_json)["ingestionTaskId"] == task_id


def test_celery_rag_ingestion_task_runs_in_eager_mode(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.3, 0.2, 0.1]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_user(db, "celery-eager-ingestion")
        task = create_ingestion_task(
            db,
            user_id=user.id,
            title="Eager RAG",
            knowledge_base="question_bank",
            original_filename="eager.md",
            visibility="private",
            metadata={},
        )
        merge_ingestion_task_input(
            db,
            task,
            {"textSnapshot": "Eager Celery task creates a RAG document."},
        )
        task_id = task.task_id

    result = run_rag_ingestion_task.delay(task_id).get(timeout=5)

    assert result["taskId"] == task_id
    assert result["status"] == "succeeded"
    assert result["documentId"]


def test_dispatch_rag_ingestion_task_keeps_task_queued_when_not_eager(monkeypatch) -> None:
    with SessionLocal() as db:
        user = create_user(db, "dispatch-queued")
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


def test_dispatch_rag_ingestion_task_marks_failed_when_broker_dispatch_fails(monkeypatch) -> None:
    with SessionLocal() as db:
        user = create_user(db, "dispatch-failed")
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

        def fake_delay(task_id: str) -> None:
            raise RuntimeError("broker offline")

        monkeypatch.setattr(run_rag_ingestion_task, "delay", fake_delay)

        result = dispatch_rag_ingestion_task(db, task)

        assert result.status == "failed"
        assert result.can_retry == 1
        assert "Celery dispatch failed: broker offline" in result.error_message
        serialized = serialize_ingestion_task(result)
        assert serialized["dispatchMode"] == "failed"


def test_execute_rag_ingestion_task_records_started_at_and_duration(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_user(db, "timed-ingestion")
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
        task_id = task.task_id

    result = execute_rag_ingestion_task(task_id)

    assert result["status"] == "succeeded"
    assert result["startedAt"]
    assert isinstance(result["durationMs"], int)
    assert result["durationMs"] >= 0
