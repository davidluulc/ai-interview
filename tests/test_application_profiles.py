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


def test_application_profiles_require_authentication() -> None:
    client = TestClient(app)

    response = client.get("/api/application-profiles")

    assert response.status_code == 401


def test_user_can_create_list_get_archive_and_restore_application_profile() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    tokens = register_and_login(client, f"profile-{suffix}@example.com", f"profile_{suffix[:10]}")

    create_response = client.post(
        "/api/application-profiles",
        headers=auth_headers(tokens),
        json={
            "title": "Python AI 应用实习投递",
            "targetRole": "AI 应用开发实习生",
            "applicationType": "实习投递",
            "resume": "做过 AI 模拟面试系统，负责 FastAPI、RAG 和鉴权。",
            "jd": "熟悉 Python、FastAPI、MySQL、Redis，了解 AI 调用。",
            "company": "希望候选人能独立完成 AI 应用接口开发。",
            "positionTag": "ai_app",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["id"]
    assert created["title"] == "Python AI 应用实习投递"
    assert created["targetRole"] == "AI 应用开发实习生"
    assert created["status"] == "active"

    list_response = client.get("/api/application-profiles", headers=auth_headers(tokens))

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    get_response = client.get(f"/api/application-profiles/{created['id']}", headers=auth_headers(tokens))

    assert get_response.status_code == 200
    assert get_response.json()["resume"].startswith("做过 AI 模拟面试系统")

    delete_response = client.delete(f"/api/application-profiles/{created['id']}", headers=auth_headers(tokens))

    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "archived"

    empty_response = client.get("/api/application-profiles", headers=auth_headers(tokens))

    assert empty_response.status_code == 200
    assert empty_response.json() == []

    archived_response = client.get("/api/application-profiles?status=archived", headers=auth_headers(tokens))

    assert archived_response.status_code == 200
    assert [item["id"] for item in archived_response.json()] == [created["id"]]

    restore_response = client.post(f"/api/application-profiles/{created['id']}/restore", headers=auth_headers(tokens))

    assert restore_response.status_code == 200
    assert restore_response.json()["status"] == "active"

    restored_list_response = client.get("/api/application-profiles", headers=auth_headers(tokens))

    assert restored_list_response.status_code == 200
    assert [item["id"] for item in restored_list_response.json()] == [created["id"]]


def test_application_profiles_are_isolated_by_user() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    user_a = register_and_login(client, f"profile-a-{suffix}@example.com", f"profile_a_{suffix[:10]}")
    user_b = register_and_login(client, f"profile-b-{suffix}@example.com", f"profile_b_{suffix[:10]}")

    create_response = client.post(
        "/api/application-profiles",
        headers=auth_headers(user_a),
        json={
            "title": "用户 A 的档案",
            "targetRole": "Python 实习生",
            "applicationType": "实习投递",
            "resume": "用户 A 的简历",
            "jd": "用户 A 的 JD",
            "company": "用户 A 的公司要求",
            "positionTag": "python",
        },
    )
    profile_id = create_response.json()["id"]

    list_b = client.get("/api/application-profiles", headers=auth_headers(user_b))
    get_b = client.get(f"/api/application-profiles/{profile_id}", headers=auth_headers(user_b))
    delete_b = client.delete(f"/api/application-profiles/{profile_id}", headers=auth_headers(user_b))

    assert list_b.status_code == 200
    assert list_b.json() == []
    assert get_b.status_code == 404
    assert delete_b.status_code == 404
