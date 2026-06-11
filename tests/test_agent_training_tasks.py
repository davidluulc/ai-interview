import json
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import AgentDecisionLog, User
from backend_python.main import app
from backend_python.training_tasks import create_or_update_training_task


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()


def test_next_question_agent_state_includes_high_priority_training_tasks(monkeypatch) -> None:
    from backend_python.routes import interview

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "lower_difficulty",
                "stage": "技术追问",
                "difficulty": "basic",
                "focus": "RAG 质量评估",
                "reason": "候选人存在低掌握度训练任务。",
                "tools": ["retrieve_context"],
                "shouldUpdateMemory": True,
            }
        return {
            "stage": "技术追问",
            "stability": "动态追问",
            "focus": "RAG 质量评估",
            "prompt": "我们先拆小一点：Hit@K 解决什么问题？",
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"agent-training-{suffix}@example.com"
    tokens = register_and_login(client, email, f"agent_training_{suffix[:8]}")

    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        assert user_id is not None
        create_or_update_training_task(
            db,
            user_id=user_id,
            weak_tag="rag_quality",
            weak_label="RAG 质量评估",
            title="RAG 质量评估专项训练",
            description="练习 Hit@K 和 MRR。",
            priority="high",
            mastery_score=45,
            metadata={"source": "test"},
        )

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI 应用开发实习生", "resume": "做过 RAG"},
            "history": [{"question": "RAG 质量怎么评估？", "answer": "不知道"}],
            "nextStage": "技术追问",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
        log = db.scalars(
            select(AgentDecisionLog)
            .where(AgentDecisionLog.user_id == user_id)
            .order_by(AgentDecisionLog.id.desc())
            .limit(1)
        ).first()
        assert log is not None
        state = json.loads(log.state_json)
        decision = json.loads(log.decision_json)

    assert state["candidateTrainingTasks"][0]["weakTag"] == "rag_quality"
    assert state["candidateTrainingTasks"][0]["masteryScore"] == 45
    assert decision["selectedTrainingTask"]["weakTag"] == "rag_quality"
    assert decision["selectedTrainingTask"]["priority"] == "high"
    assert "训练任务" in decision["selectedTrainingTask"]["reason"]
