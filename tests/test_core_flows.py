from fastapi.testclient import TestClient
from uuid import uuid4

from backend_python.main import app
from backend_python.position_agent import match_positions
from backend_python.question_rag import retrieve_questions
from backend_python.rag import retrieve_role_context


def auth_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"core-flow-user-{suffix}@example.com"
    username = f"core_flow_{suffix[:12]}"
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def test_position_agent_recommends_ai_app_role() -> None:
    profile = {
        "targetRole": "AI 应用开发实习生",
        "resume": "我做过 AI 模拟面试系统，使用 Python FastAPI 调用 Qwen，并设计 RAG。",
        "jd": "要求熟悉大模型 API、RAG、Prompt、Python 后端。",
    }

    matches = match_positions(profile)

    assert matches
    assert matches[0]["position_tag"] == "ai_app_intern"
    assert matches[0]["score"] > 0


def test_question_rag_returns_scored_question() -> None:
    profile = {
        "targetRole": "AI 应用开发实习生",
        "positionTag": "ai_app_intern",
        "resume": "FastAPI Qwen RAG 模拟面试系统",
        "jd": "大模型 API、RAG、Agent、Python 后端",
    }

    questions = retrieve_questions(profile, "技术追问")

    assert questions
    assert questions[0]["score"] > 0
    assert "question" in questions[0]


def test_role_knowledge_rag_returns_evidence() -> None:
    profile = {
        "targetRole": "AI 应用开发实习生",
        "resume": "FastAPI Qwen RAG 模拟面试系统",
        "jd": "大模型 API、RAG、Agent、Python 后端",
    }

    items = retrieve_role_context(profile, "技术追问")

    assert items
    assert items[0]["score"] > 0
    assert "matchedKeywords" in items[0]


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["redis"]["enabled"] is False
    assert response.json()["redis"]["status"] == "disabled"
    assert response.json()["infrastructure"]["database"]["dialect"]
    assert response.json()["infrastructure"]["redis"]["status"] == "disabled"
    assert response.json()["infrastructure"]["celery"]["status"] in {"eager", "configured"}
    assert response.json()["infrastructure"]["celery"]["mode"] in {"eager", "worker"}
    assert "workerCommand" in response.json()["infrastructure"]["celery"]
    assert "X-Process-Time-Ms" in response.headers


def test_validation_error_uses_standard_error_shape() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/interview/next-question",
        headers=auth_headers(client),
        json={"history": "not-a-list"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
