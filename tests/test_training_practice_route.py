from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import TrainingTask, User
from backend_python.main import app
from backend_python.training_tasks import create_or_update_training_task


def create_authenticated_client() -> tuple[TestClient, dict[str, str], int]:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"training-practice-{suffix}@example.com"
    username = f"training_practice_{suffix[:8]}"
    register = client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    assert register.status_code == 200
    login = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user_id = user.id
    return client, {"Authorization": f"Bearer {login.json()['accessToken']}"}, user_id


def create_task_for_user(user_id: int, weak_tag: str = "rag_quality") -> TrainingTask:
    with SessionLocal() as db:
        task = create_or_update_training_task(
            db,
            user_id=user_id,
            weak_tag=weak_tag,
            weak_label=weak_tag,
            title=f"{weak_tag} 专项训练",
            description=f"练习 {weak_tag}。",
            priority="high",
            mastery_score=45,
            metadata={"source": "route-test"},
        )
        db.expunge(task)
        return task


def test_get_training_practice_returns_template_payload() -> None:
    client, headers, user_id = create_authenticated_client()
    task = create_task_for_user(user_id, "rag_quality")

    response = client.get(f"/api/training/tasks/{task.id}/practice?mode=coach&difficulty=basic", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["task"]["id"] == task.id
    assert body["practice"]["weakTag"] == "rag_quality"
    assert body["practice"]["question"]
    assert body["practice"]["answerKeyPoints"]


def test_complete_training_task_accepts_answer_text_and_self_rating() -> None:
    client, headers, user_id = create_authenticated_client()
    task = create_task_for_user(user_id, "agent_state")

    response = client.post(
        f"/api/training/tasks/{task.id}/complete",
        headers=headers,
        json={
            "answerStatus": "完整",
            "answerText": "Agent State 是当前面试局面的事实快照。",
            "selfRating": 4,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["attemptCount"] == 1
    assert body["masteryScore"] > 40
    assert body["metadata"]["lastPractice"]["answerStatus"] == "完整"
    assert body["metadata"]["lastPractice"]["selfRating"] == 4
    assert "Agent State" in body["metadata"]["lastPractice"]["answerPreview"]


def test_complete_training_task_returns_coach_review_and_ignores_duplicate_submission() -> None:
    client, headers, user_id = create_authenticated_client()
    task = create_task_for_user(user_id, "rag_quality")
    payload = {
        "answerStatus": "模糊",
        "answerText": "Hit@K 和 MRR 可以用来评估 RAG 召回质量。",
        "selfRating": 3,
    }

    first = client.post(f"/api/training/tasks/{task.id}/complete", headers=headers, json=payload)
    second = client.post(f"/api/training/tasks/{task.id}/complete", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    review = first_body["metadata"]["lastPractice"]["review"]
    assert review["referenceAnswer"]
    assert review["rewrittenAnswer"]
    assert review["nextPractice"]
    assert review["score"] >= 0
    assert any("Hit@K" in item for item in review["strengths"])
    assert review["issues"]
    assert review["missingKeyPoints"]
    assert first_body["attemptCount"] == 1
    assert second_body["attemptCount"] == 1
    assert second_body["masteryScore"] == first_body["masteryScore"]
    assert second_body["metadata"]["lastPractice"]["duplicateSubmission"] is True
