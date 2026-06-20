from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import User
from backend_python.main import app


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def register_login_user(client: TestClient, *, role: str = "user") -> tuple[dict, int]:
    suffix = uuid4().hex
    email = f"admin-users-{role}-{suffix}@example.com"
    username = f"admin_users_{role}_{suffix[:8]}"
    client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    if role == "admin":
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            user.role = "admin"
            db.commit()
    tokens = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        return tokens, user.id


def test_admin_can_force_logout_user_sessions() -> None:
    client = TestClient(app)
    admin_tokens, _ = register_login_user(client, role="admin")
    user_tokens, user_id = register_login_user(client)

    response = client.post(f"/api/admin/users/{user_id}/force-logout", headers=auth_headers(admin_tokens))

    assert response.status_code == 200
    assert response.json()["revokedSessions"] >= 1
    assert response.json()["revokedRefreshTokens"] >= 1
    me_response = client.get("/api/auth/me", headers=auth_headers(user_tokens))
    refresh_response = client.post("/api/auth/refresh", json={"refreshToken": user_tokens["refreshToken"]})
    assert me_response.status_code == 401
    assert me_response.json()["error"]["code"] == "session_revoked"
    assert refresh_response.status_code == 401


def test_force_logout_requires_admin() -> None:
    client = TestClient(app)
    user_tokens, _ = register_login_user(client)
    _, target_user_id = register_login_user(client)

    response = client.post(f"/api/admin/users/{target_user_id}/force-logout", headers=auth_headers(user_tokens))

    assert response.status_code == 403
