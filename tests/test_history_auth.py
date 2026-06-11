from uuid import uuid4

from fastapi.testclient import TestClient

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
    return response.json()


def save_history(client: TestClient, access_token: str, candidate_name: str, score: int) -> None:
    response = client.post(
        "/api/history",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "profile": {
                "candidateName": candidate_name,
                "targetRole": "AI 应用开发实习生",
                "applicationType": "实习",
            },
            "answers": [{"stage": "技术追问", "answer": "我会解释 RAG 流程"}],
            "report": {"score": score, "risks": [f"{candidate_name} 风险"], "actions": [f"{candidate_name} 训练"]},
        },
    )

    assert response.status_code == 200


def test_history_requires_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/history")

    assert response.status_code == 401


def test_history_records_are_isolated_by_user() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user_a = register_and_login(client, f"user-a-{suffix}@example.com", f"user_a_{suffix[:10]}")
    user_b = register_and_login(client, f"user-b-{suffix}@example.com", f"user_b_{suffix[:10]}")

    save_history(client, user_a["accessToken"], "用户A", 81)
    save_history(client, user_b["accessToken"], "用户B", 92)

    response_a = client.get(
        "/api/history",
        headers={"Authorization": f"Bearer {user_a['accessToken']}"},
    )
    response_b = client.get(
        "/api/history",
        headers={"Authorization": f"Bearer {user_b['accessToken']}"},
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert len(response_a.json()) == 1
    assert len(response_b.json()) == 1
    assert response_a.json()[0]["profile"]["candidateName"] == "用户A"
    assert response_b.json()[0]["profile"]["candidateName"] == "用户B"


def test_history_stats_are_isolated_by_user() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user_c = register_and_login(client, f"user-c-{suffix}@example.com", f"user_c_{suffix[:10]}")
    user_d = register_and_login(client, f"user-d-{suffix}@example.com", f"user_d_{suffix[:10]}")

    save_history(client, user_c["accessToken"], "用户C", 70)
    save_history(client, user_d["accessToken"], "用户D", 95)

    response = client.get(
        "/api/history/stats",
        headers={"Authorization": f"Bearer {user_c['accessToken']}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["latestScore"] == 70
