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
    assert response.status_code == 200
    return response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def create_profile(client: TestClient, tokens: dict, title: str) -> dict:
    response = client.post(
        "/api/application-profiles",
        headers=auth_headers(tokens),
        json={
            "title": title,
            "targetRole": "Python AI 应用实习生",
            "applicationType": "实习投递",
            "resume": "做过 AI 模拟面试系统",
            "jd": "熟悉 Python、FastAPI、RAG",
            "company": "希望能解释项目架构",
            "positionTag": "ai_app",
        },
    )
    assert response.status_code == 200
    return response.json()


def save_history(client: TestClient, tokens: dict, application_profile_id: int) -> dict:
    response = client.post(
        "/api/history",
        headers=auth_headers(tokens),
        json={
            "applicationProfileId": application_profile_id,
            "profile": {
                "candidateName": "David",
                "targetRole": "Python AI 应用实习生",
                "applicationType": "实习投递",
            },
            "answers": [{"stage": "项目深挖", "answer": "我负责用户系统和 RAG 调试。"}],
            "report": {"score": 88, "risks": ["项目指标要补充"], "actions": ["准备架构图"]},
        },
    )
    return response


def test_history_can_be_linked_to_owned_application_profile() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(client, f"history-profile-{suffix}@example.com", f"history_profile_{suffix[:8]}")
    profile = create_profile(client, tokens, "Python AI 应用投递档案")

    save_response = save_history(client, tokens, profile["id"])

    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["applicationProfile"]["id"] == profile["id"]
    assert saved["applicationProfile"]["title"] == "Python AI 应用投递档案"

    list_response = client.get("/api/history", headers=auth_headers(tokens))

    assert list_response.status_code == 200
    listed = list_response.json()[0]
    assert listed["applicationProfile"]["id"] == profile["id"]
    assert listed["applicationProfile"]["targetRole"] == "Python AI 应用实习生"


def test_history_rejects_application_profile_owned_by_another_user() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    owner = register_and_login(client, f"owner-{suffix}@example.com", f"owner_{suffix[:10]}")
    other = register_and_login(client, f"other-{suffix}@example.com", f"other_{suffix[:10]}")
    owner_profile = create_profile(client, owner, "别人的投递档案")

    response = save_history(client, other, owner_profile["id"])

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Application profile not found"
