from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.auth import (
    create_access_token,
    decode_token,
    hash_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from backend_python.main import app


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def test_password_hash_is_not_plaintext_and_can_be_verified() -> None:
    hashed = hash_password("password123")

    assert hashed != "password123"
    assert verify_password("password123", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_contains_user_id_and_type() -> None:
    token = create_access_token(user_id=42)

    payload = decode_token(token, expected_type="access")

    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_refresh_token_hash_can_be_verified_without_storing_plain_token() -> None:
    plain_token = "refresh-token-value"
    hashed = hash_refresh_token(plain_token)

    assert hashed != plain_token
    assert verify_refresh_token(plain_token, hashed) is True
    assert verify_refresh_token("other-token", hashed) is False


def test_register_login_me_and_logout_flow() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"student-{suffix}@example.com"
    username = f"student_{suffix[:12]}"

    register_response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "password123",
        },
    )

    assert register_response.status_code == 200
    assert register_response.json()["email"] == email
    assert "password" not in register_response.json()

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )

    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["tokenType"] == "bearer"
    assert tokens["accessToken"]
    assert tokens["refreshToken"]

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == email

    logout_response = client.post(
        "/api/auth/logout",
        json={"refreshToken": tokens["refreshToken"]},
    )

    assert logout_response.status_code == 200
    assert logout_response.json()["ok"] is True

    refresh_response = client.post(
        "/api/auth/refresh",
        json={"refreshToken": tokens["refreshToken"]},
    )

    assert refresh_response.status_code == 401


def test_login_rejects_wrong_password() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"wrong-password-{suffix}@example.com"
    username = f"wrong_password_{suffix[:12]}"
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
        json={"email": email, "password": "bad-password"},
    )

    assert response.status_code == 401


def test_logout_blacklists_current_access_token() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"blacklist-access-{suffix}@example.com"
    username = f"blacklist_access_{suffix[:12]}"
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "password123",
        },
    )
    login_response = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    tokens = login_response.json()

    logout_response = client.post(
        "/api/auth/logout",
        headers=auth_headers(tokens),
        json={"refreshToken": tokens["refreshToken"]},
    )
    assert logout_response.status_code == 200

    me_response = client.get("/api/auth/me", headers=auth_headers(tokens))

    assert me_response.status_code == 401
