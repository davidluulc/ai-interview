import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import RagIngestionTask
from backend_python.main import app
from backend_python.security import reset_security_state


@pytest.fixture(autouse=True)
def reset_security_between_tests() -> None:
    reset_security_state()


def register_and_login(client: TestClient, prefix: str) -> dict:
    suffix = uuid4().hex
    email = f"{prefix}-{suffix}@example.com"
    username = f"{prefix}_{suffix[:10]}"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    assert response.status_code == 200
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200
    return login_response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def test_upload_text_document_creates_rag_document(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_text")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={
            "title": "FastAPI Depends 资料",
            "knowledgeBase": "role_knowledge",
            "visibility": "private",
            "metadata": '{"positionTag":"python_backend"}',
        },
        files={
            "file": (
                "depends.txt",
                b"FastAPI Depends is dependency injection.\n\nRAG chunk metadata records source.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["document"]["title"] == "FastAPI Depends 资料"
    assert body["document"]["sourceType"] == "upload"
    assert body["document"]["metadata"]["originalFilename"] == "depends.txt"
    assert body["preview"]["chunkCount"] >= 1
    assert body["taskId"].startswith("rag_ingestion-")

    task_response = client.get(
        f"/api/rag/documents/ingestion-tasks/{body['taskId']}",
        headers=auth_headers(tokens),
    )
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "succeeded"
    assert task_response.json()["result"]["document"]["id"] == body["document"]["id"]

    with SessionLocal() as db:
        persisted_task = db.scalar(select(RagIngestionTask).where(RagIngestionTask.task_id == body["taskId"]))
        assert persisted_task is not None
        assert persisted_task.status == "succeeded"
        assert persisted_task.document_id == body["document"]["id"]
        input_payload = json.loads(persisted_task.input_json)
        assert input_payload["metadata"]["positionTag"] == "python_backend"
        assert input_payload["textSnapshot"].startswith("FastAPI Depends")


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


def test_upload_same_file_returns_existing_ingestion_task(monkeypatch) -> None:
    reset_security_state()

    async def fake_embed_text(text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_idempotent")
    payload = {
        "title": "Idempotent Upload",
        "knowledgeBase": "role_knowledge",
        "visibility": "private",
    }

    first = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data=payload,
        files={"file": ("same.txt", b"same idempotent content", "text/plain")},
    )
    second = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data=payload,
        files={"file": ("same.txt", b"same idempotent content", "text/plain")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["taskId"] == first.json()["taskId"]
    assert second.json()["idempotencyHit"] is True


def test_upload_markdown_document_preserves_heading_text(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.4, 0.5, 0.6]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_md")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "RAG Markdown", "knowledgeBase": "question_bank", "visibility": "private"},
        files={"file": ("rag.md", "# RAG 标题\n\n## Chunk 切分\n\nmetadata filter", "text/markdown")},
    )

    assert response.status_code == 200
    document_id = response.json()["document"]["id"]
    detail_response = client.get(f"/api/rag/documents/{document_id}", headers=auth_headers(tokens))
    assert detail_response.status_code == 200
    chunk_text = "\n".join(chunk["content"] for chunk in detail_response.json()["chunks"])
    assert "# RAG 标题" in chunk_text
    assert "metadata filter" in chunk_text


def test_upload_rejects_unsupported_file_type() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_bad_type")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "表格", "knowledgeBase": "role_knowledge", "visibility": "private"},
        files={"file": ("bad.xlsx", b"not supported", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["error"]["message"]

    tasks_response = client.get("/api/rag/documents/ingestion-tasks", headers=auth_headers(tokens))
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()["items"]
    assert tasks
    assert tasks[0]["status"] == "failed"
    assert tasks[0]["canRetry"] is False
    assert "Unsupported file type" in tasks[0]["error"]

    retry_response = client.post(
        f"/api/rag/documents/ingestion-tasks/{tasks[0]['taskId']}/retry",
        headers=auth_headers(tokens),
    )
    assert retry_response.status_code == 409


def test_upload_rejects_invalid_metadata_json() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_bad_metadata")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={
            "title": "Invalid metadata",
            "knowledgeBase": "role_knowledge",
            "visibility": "private",
            "metadata": "[]",
        },
        files={"file": ("metadata.txt", b"RAG metadata must be object.", "text/plain")},
    )

    assert response.status_code == 400
    assert "metadata must be a JSON object" in response.json()["error"]["message"]

    tasks_response = client.get("/api/rag/documents/ingestion-tasks", headers=auth_headers(tokens))
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()["items"]
    assert tasks
    assert tasks[0]["status"] == "failed"
    assert "metadata must be a JSON object" in tasks[0]["error"]


def test_retry_ingestion_task_dispatches_celery_task(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.2, 0.3, 0.4]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_retry")

    upload_response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "Retry doc", "knowledgeBase": "role_knowledge", "visibility": "private"},
        files={"file": ("retry.txt", b"Retry should reuse the Celery ingestion path.", "text/plain")},
    )
    assert upload_response.status_code == 200
    task_id = upload_response.json()["taskId"]

    with SessionLocal() as db:
        task = db.scalar(select(RagIngestionTask).where(RagIngestionTask.task_id == task_id))
        assert task is not None
        task.status = "failed"
        task.error_message = "Simulated transient failure."
        task.can_retry = 1
        task.document_id = None
        db.add(task)
        db.commit()

    from backend_python.rag_ingestion_tasks import execute_rag_ingestion_task
    from backend_python.tasks.rag_ingestion import run_rag_ingestion_task

    dispatched_task_ids: list[str] = []

    class FakeAsyncResult:
        def get(self, timeout: int | None = None) -> dict:
            return {"ok": True, "timeout": timeout}

    def fake_delay(dispatched_task_id: str) -> FakeAsyncResult:
        dispatched_task_ids.append(dispatched_task_id)
        execute_rag_ingestion_task(dispatched_task_id)
        return FakeAsyncResult()

    monkeypatch.setattr(run_rag_ingestion_task, "delay", fake_delay)

    retry_response = client.post(
        f"/api/rag/documents/ingestion-tasks/{task_id}/retry",
        headers=auth_headers(tokens),
    )

    assert retry_response.status_code == 200
    body = retry_response.json()
    assert dispatched_task_ids == [task_id]
    assert body["status"] == "succeeded"
    assert body["retryCount"] == 1
    assert body["document"]["sourceType"] == "upload_retry"
    assert body["retryLockedAt"]


def test_retry_returns_queued_in_worker_mode(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.2, 0.3, 0.4]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
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
    assert body["retryLockedAt"]


def test_retry_running_ingestion_task_returns_409(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.2, 0.3, 0.4]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    tokens = register_and_login(client, "rag_retry_conflict")

    upload_response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "Retry Conflict", "knowledgeBase": "role_knowledge", "visibility": "private"},
        files={"file": ("retry-conflict.txt", b"Retry conflict content.", "text/plain")},
    )
    assert upload_response.status_code == 200
    task_id = upload_response.json()["taskId"]

    with SessionLocal() as db:
        task = db.scalar(select(RagIngestionTask).where(RagIngestionTask.task_id == task_id))
        assert task is not None
        task.status = "running"
        task.error_message = ""
        task.can_retry = 1
        db.add(task)
        db.commit()

    response = client.post(
        f"/api/rag/documents/ingestion-tasks/{task_id}/retry",
        headers=auth_headers(tokens),
    )

    assert response.status_code == 409
    assert "processing" in response.text.lower() or "already" in response.text.lower()


def test_user_cannot_read_other_users_ingestion_task(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [0.7, 0.8, 0.9]

    monkeypatch.setattr("backend_python.rag_store.embed_text", fake_embed_text)
    client = TestClient(app)
    owner_tokens = register_and_login(client, "rag_upload_owner")
    other_tokens = register_and_login(client, "rag_upload_other")

    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(owner_tokens),
        data={"title": "Owner doc", "knowledgeBase": "role_knowledge", "visibility": "private"},
        files={"file": ("owner.txt", b"Only the owner should see this ingestion task.", "text/plain")},
    )

    assert response.status_code == 200
    task_id = response.json()["taskId"]
    other_response = client.get(
        f"/api/rag/documents/ingestion-tasks/{task_id}",
        headers=auth_headers(other_tokens),
    )
    assert other_response.status_code == 404
