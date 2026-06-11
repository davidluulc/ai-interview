from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.agent_logging import create_agent_decision_log
from backend_python.database import SessionLocal, init_db
from backend_python.db_models import User
from backend_python.main import app


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def test_agent_logs_require_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/agent/logs/recent")

    assert response.status_code == 401


def test_recent_agent_logs_are_isolated_by_user() -> None:
    init_db()
    client = TestClient(app)
    suffix = uuid4().hex
    user_a = register_and_login(client, f"agent-a-{suffix}@example.com", f"agent_a_{suffix[:8]}")
    user_b = register_and_login(client, f"agent-b-{suffix}@example.com", f"agent_b_{suffix[:8]}")

    with SessionLocal() as db:
        users = db.query(User).filter(User.email.in_([f"agent-a-{suffix}@example.com", f"agent-b-{suffix}@example.com"])).all()
        user_by_email = {user.email: user for user in users}
        create_agent_decision_log(
            db,
            user_id=user_by_email[f"agent-a-{suffix}@example.com"].id,
            application_profile_id=None,
            request_type="next_question",
            state={"roundCount": 1, "answerStatus": "不会"},
            decision={
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 日志字段",
                "reason": "用户回答不知道，先降低难度。",
                "tools": ["retrieve_context", "generate_question"],
                "fallbackUsed": False,
            },
        )
        create_agent_decision_log(
            db,
            user_id=user_by_email[f"agent-b-{suffix}@example.com"].id,
            application_profile_id=None,
            request_type="next_question",
            state={"roundCount": 1, "answerStatus": "完整"},
            decision={
                "nextAction": "raise_difficulty",
                "stage": "系统设计",
                "difficulty": "hard",
                "focus": "部署上线",
                "reason": "另一个用户的日志不应该被看到。",
                "tools": ["generate_question"],
                "fallbackUsed": False,
            },
        )

    response = client.get("/api/agent/logs/recent", headers=auth_headers(user_a))

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["nextAction"] == "lower_difficulty"
    assert items[0]["focus"] == "RAG 日志字段"
    assert items[0]["state"]["answerStatus"] == "不会"
