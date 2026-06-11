from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import RagRetrievalLog, User
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


def test_admin_rag_quality_summary_returns_low_quality_recall_items() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"rag-quality-admin-{suffix}@example.com"
    register_and_login(client, email, f"rag_quality_admin_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {admin['accessToken']}"}

    with SessionLocal() as db:
        admin_user = db.scalar(select(User).where(User.email == email))
        assert admin_user is not None
        db.add_all(
            [
                RagRetrievalLog(
                    user_id=admin_user.id,
                    request_type="interview",
                    query_text="empty recall query",
                    retriever_name="role_knowledge",
                    retrieval_mode="bm25",
                    hit_count=0,
                    hits_json="[]",
                    used_in_prompt=1,
                ),
                RagRetrievalLog(
                    user_id=admin_user.id,
                    request_type="interview",
                    query_text="weak recall query",
                    retriever_name="question_bank",
                    retrieval_mode="hybrid",
                    hit_count=1,
                    hits_json='[{"title":"weak","score":0.1}]',
                    used_in_prompt=1,
                ),
                RagRetrievalLog(
                    user_id=admin_user.id,
                    request_type="interview",
                    query_text="unused recall query",
                    retriever_name="candidate_memory",
                    retrieval_mode="bm25",
                    hit_count=1,
                    hits_json='[{"title":"unused","score":9.0}]',
                    used_in_prompt=0,
                ),
            ]
        )
        db.commit()

    response = client.get("/api/admin/rag/quality", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["totalLogCount"] >= 3
    assert body["summary"]["emptyRecallCount"] >= 1
    assert body["summary"]["weakRecallCount"] >= 1
    assert body["summary"]["unusedInPromptCount"] >= 1
    assert body["summary"]["lowQualityCount"] >= 3
    item_by_query = {item["queryText"]: item for item in body["items"]}
    assert item_by_query["empty recall query"]["issueType"] == "empty_recall"
    assert item_by_query["weak recall query"]["issueType"] == "weak_recall"
    assert item_by_query["unused recall query"]["issueType"] == "unused_in_prompt"
