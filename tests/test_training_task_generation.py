from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.main import app


def register_and_login(client: TestClient, email: str, username: str) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    return response.json()


def test_training_tasks_require_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/training/tasks")

    assert response.status_code == 401


def test_generate_training_tasks_from_report_weak_tags_and_deduplicate() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user = register_and_login(client, f"training-api-{suffix}@example.com", f"training_api_{suffix[:8]}")
    headers = {"Authorization": f"Bearer {user['accessToken']}"}
    payload = {
        "report": {
            "questionReviews": [
                {"focus": "RAG 质量评估", "weakTags": ["rag_quality"]},
                {"focus": "Agent State", "weakTags": ["agent_state", "rag_quality"]},
            ],
            "trainingPlan": {
                "weakTopics": [
                    {"focus": "RAG 质量评估", "weakTags": ["rag_quality"], "trainingAction": "练习 Hit@K 和 MRR"}
                ]
            },
        }
    }

    first = client.post("/api/training/tasks/generate-from-report", headers=headers, json=payload)
    second = client.post("/api/training/tasks/generate-from-report", headers=headers, json=payload)
    listing = client.get("/api/training/tasks", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert listing.status_code == 200
    body = listing.json()
    weak_tags = sorted(item["weakTag"] for item in body["items"])
    assert weak_tags == ["agent_state", "rag_quality"]
    assert len(body["items"]) == 2
    assert all(item["masteryScore"] <= 60 for item in body["items"])


def test_training_task_lifecycle_endpoints_are_user_isolated() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user_a = register_and_login(client, f"task-a-{suffix}@example.com", f"task_a_{suffix[:8]}")
    user_b = register_and_login(client, f"task-b-{suffix}@example.com", f"task_b_{suffix[:8]}")
    headers_a = {"Authorization": f"Bearer {user_a['accessToken']}"}
    headers_b = {"Authorization": f"Bearer {user_b['accessToken']}"}

    created = client.post(
        "/api/training/tasks/generate-from-report",
        headers=headers_a,
        json={"report": {"questionReviews": [{"focus": "RAG", "weakTags": ["rag_quality"]}]}},
    ).json()["items"][0]
    task_id = created["id"]

    forbidden = client.post(f"/api/training/tasks/{task_id}/start", headers=headers_b)
    started = client.post(f"/api/training/tasks/{task_id}/start", headers=headers_a)
    completed = client.post(f"/api/training/tasks/{task_id}/complete", headers=headers_a, json={"answerStatus": "完整"})
    archived = client.post(f"/api/training/tasks/{task_id}/archive", headers=headers_a)

    assert forbidden.status_code == 404
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert completed.status_code == 200
    assert completed.json()["attemptCount"] == 1
    assert completed.json()["masteryScore"] > created["masteryScore"]
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
