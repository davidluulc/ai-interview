from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import RagIngestionTask, User
from backend_python.main import app


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()


def promote_to_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = "admin"
        db.commit()


def test_admin_lists_rag_ingestion_tasks_with_failure_summary() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    admin_email = f"rag-ingestion-admin-{suffix}@example.com"
    owner_email = f"rag-ingestion-owner-{suffix}@example.com"
    register_and_login(client, admin_email, f"ingestion_admin_{suffix[:8]}")
    register_and_login(client, owner_email, f"ingestion_owner_{suffix[:8]}")
    promote_to_admin(admin_email)
    admin = client.post("/api/auth/login", json={"email": admin_email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {admin['accessToken']}"}

    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == owner_email))
        assert owner is not None
        db.add_all(
            [
                RagIngestionTask(
                    task_id=f"rag_ingestion-failed-{suffix}",
                    user_id=owner.id,
                    title="Broken upload",
                    knowledge_base="role_knowledge",
                    original_filename="broken.md",
                    status="failed",
                    progress=100,
                    error_message="Parsed empty text from uploaded file.",
                    can_retry=0,
                ),
                RagIngestionTask(
                    task_id=f"rag_ingestion-retryable-{suffix}",
                    user_id=owner.id,
                    title="Retryable upload",
                    knowledge_base="question_bank",
                    original_filename="retryable.md",
                    status="failed",
                    progress=100,
                    error_message="document create failed",
                    can_retry=1,
                    input_json='{"textSnapshot":"retryable text"}',
                ),
            ]
        )
        db.commit()

    response = client.get("/api/admin/rag/ingestion-tasks", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["failedCount"] >= 2
    assert body["summary"]["retryableCount"] >= 1
    item_by_task_id = {item["taskId"]: item for item in body["items"]}
    failed_item = item_by_task_id[f"rag_ingestion-failed-{suffix}"]
    retryable_item = item_by_task_id[f"rag_ingestion-retryable-{suffix}"]
    assert failed_item["userEmail"] == owner_email
    assert failed_item["error"] == "Parsed empty text from uploaded file."
    assert retryable_item["canRetry"] is True


def test_regular_user_cannot_list_admin_ingestion_tasks() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(
        client,
        f"rag-ingestion-user-{suffix}@example.com",
        f"ingestion_user_{suffix[:8]}",
    )
    headers = {"Authorization": f"Bearer {tokens['accessToken']}"}

    response = client.get("/api/admin/rag/ingestion-tasks", headers=headers)

    assert response.status_code == 403
