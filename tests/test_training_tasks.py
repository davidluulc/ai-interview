from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import User
from backend_python.main import app


def create_user() -> User:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"training-user-{suffix}@example.com"
    username = f"training_user_{suffix[:8]}"
    response = client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    assert response.status_code == 200
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        db.expunge(user)
        return user


def test_create_or_update_training_task_deduplicates_active_task() -> None:
    from backend_python.db_models import TrainingTask
    from backend_python.training_tasks import create_or_update_training_task

    user = create_user()
    with SessionLocal() as db:
        first = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="rag_quality",
            weak_label="RAG 质量评估",
            title="RAG 质量评估基础训练",
            description="练习 Hit@K、MRR 和关键词覆盖率。",
            priority="high",
            mastery_score=30,
            metadata={"source": "report"},
        )
        second = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="rag_quality",
            weak_label="RAG 质量评估",
            title="RAG 质量评估复练",
            description="继续练习 RAG 质量指标。",
            priority="high",
            mastery_score=45,
            metadata={"source": "retry"},
        )
        tasks = db.scalars(select(TrainingTask).where(TrainingTask.user_id == user.id)).all()

    assert first.id == second.id
    assert len(tasks) == 1
    assert tasks[0].title == "RAG 质量评估复练"
    assert tasks[0].mastery_score == 45


def test_complete_training_task_updates_mastery_and_status() -> None:
    from backend_python.training_tasks import complete_training_task, create_or_update_training_task, serialize_training_task

    user = create_user()
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="agent_state",
            weak_label="Agent 状态决策",
            title="Agent State 训练",
            description="练习 Agent State、ToolCalls 和 Decision。",
            priority="medium",
            mastery_score=70,
            metadata={},
        )
        completed = complete_training_task(db, task.id, user_id=user.id, answer_status="完整")
        data = serialize_training_task(completed)

    assert data["attemptCount"] == 1
    assert data["masteryScore"] == 85
    assert data["status"] == "done"
    assert data["lastPracticedAt"]


def test_complete_training_task_clamps_mastery_score() -> None:
    from backend_python.training_tasks import complete_training_task, create_or_update_training_task

    user = create_user()
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="backend_fastapi",
            weak_label="FastAPI 后端",
            title="FastAPI 训练",
            description="练习后端模块化。",
            priority="high",
            mastery_score=3,
            metadata={},
        )
        completed = complete_training_task(db, task.id, user_id=user.id, answer_status="不会")

    assert completed.mastery_score == 0
    assert completed.status == "in_progress"


def test_build_training_practice_payload_uses_weak_tag_template() -> None:
    from backend_python.training_tasks import build_training_practice_payload, create_or_update_training_task

    user = create_user()
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="rag_quality",
            weak_label="RAG 质量评估",
            title="RAG 质量评估专项训练",
            description="练习 RAG 评估指标。",
            priority="high",
            mastery_score=45,
            metadata={"source": "report"},
        )
        payload = build_training_practice_payload(task, mode="coach", difficulty="basic")

    assert payload["weakTag"] == "rag_quality"
    assert payload["weakLabel"] == "RAG 质量评估"
    assert payload["mode"] == "coach"
    assert payload["difficulty"] == "basic"
    assert payload["question"]
    assert "Hit@K" in payload["answerKeyPoints"]
    assert payload["commonMistakes"]
    assert payload["oneMinuteTemplate"]
    assert payload["rubric"]


def test_build_training_practice_payload_normalizes_mode_and_difficulty() -> None:
    from backend_python.training_tasks import build_training_practice_payload, create_or_update_training_task

    user = create_user()
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user.id,
            weak_tag="unknown_tag",
            weak_label="未知薄弱点",
            title="兜底训练",
            description="兜底表达训练。",
            priority="medium",
            mastery_score=30,
            metadata={},
        )
        payload = build_training_practice_payload(task, mode="bad", difficulty="bad")

    assert payload["mode"] == "coach"
    assert payload["difficulty"] == "basic"
    assert payload["question"]
    assert payload["fallbackUsed"] is True
