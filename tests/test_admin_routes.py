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
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()


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
    register_and_login(client, email, f"summary_admin_{suffix[:8]}")
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


def test_admin_can_list_users_documents_and_logs() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"admin-list-{suffix}@example.com"
    register_and_login(client, email, f"admin_list_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    headers = {"Authorization": f"Bearer {admin['accessToken']}"}

    with SessionLocal() as db:
        admin_user = db.scalar(select(User).where(User.email == email))
        assert admin_user is not None
        db.add(
            RagDocument(
                user_id=admin_user.id,
                title="后台 RAG 文档",
                knowledge_base="question_bank",
                content="后台可查看的题库文档",
                metadata_json='{"source":"admin-test"}',
                chunk_count=2,
            )
        )
        db.add(
            RagRetrievalLog(
                user_id=admin_user.id,
                request_type="interview",
                query_text="RAG 质量评估",
                retriever_name="question_bank",
                retrieval_mode="hybrid",
                hit_count=2,
                hits_json='[{"id":1,"score":0.91}]',
            )
        )
        db.add(
            AgentDecisionLog(
                user_id=admin_user.id,
                request_type="next_question",
                next_action="deepen",
                stage="技术追问",
                difficulty="medium",
                focus="RAG 质量评估",
                reason="用户回答较完整，继续深挖。",
                tools_json='["role_knowledge","question_bank"]',
                state_json='{"roundCount":2}',
                decision_json='{"nextAction":"deepen"}',
            )
        )
        db.commit()

    users = client.get("/api/admin/users", headers=headers)
    documents = client.get("/api/admin/rag/documents", headers=headers)
    rag_logs = client.get("/api/admin/rag/logs", headers=headers)
    agent_logs = client.get("/api/admin/agent/logs", headers=headers)

    assert users.status_code == 200
    assert documents.status_code == 200
    assert rag_logs.status_code == 200
    assert agent_logs.status_code == 200

    assert any(item["email"] == email and item["role"] == "admin" for item in users.json()["items"])
    assert any(item["title"] == "后台 RAG 文档" and item["knowledgeBase"] == "question_bank" for item in documents.json()["items"])
    assert any(item["queryText"] == "RAG 质量评估" and item["retrievalMode"] == "hybrid" for item in rag_logs.json()["items"])
    assert any(item["focus"] == "RAG 质量评估" and item["nextAction"] == "deepen" for item in agent_logs.json()["items"])


def test_admin_lists_reject_regular_user() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user = register_and_login(client, f"admin-list-user-{suffix}@example.com", f"admin_list_user_{suffix[:8]}")
    headers = {"Authorization": f"Bearer {user['accessToken']}"}

    for path in [
        "/api/admin/users",
        "/api/admin/rag/documents",
        "/api/admin/rag/logs",
        "/api/admin/agent/logs",
    ]:
        response = client.get(path, headers=headers)
        assert response.status_code == 403
