from fastapi.testclient import TestClient

from backend_python.main import app
from backend_python.security import (
    MemoryRateLimitStore,
    MemoryTokenBlacklist,
    RateLimiter,
    RateLimitRule,
    build_security_status,
    hash_token,
    reset_security_state,
)


def test_memory_token_blacklist_rejects_blacklisted_token() -> None:
    blacklist = MemoryTokenBlacklist()
    token = "access-token-value"

    assert blacklist.contains(hash_token(token)) is False

    blacklist.add(hash_token(token), ttl_seconds=60)

    assert blacklist.contains(hash_token(token)) is True


def test_rate_limiter_blocks_after_limit() -> None:
    store = MemoryRateLimitStore()
    limiter = RateLimiter(store=store, rules={"auth.login": RateLimitRule(limit=2, window_seconds=60)})

    first = limiter.check("auth.login", "ip:127.0.0.1")
    second = limiter.check("auth.login", "ip:127.0.0.1")
    third = limiter.check("auth.login", "ip:127.0.0.1")

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after_seconds > 0


def test_security_status_exposes_safe_summary() -> None:
    status = build_security_status(
        token_blacklist_backend="memory",
        rate_limit_backend="memory",
        idempotency_backend="database",
    )

    assert status["tokenBlacklist"]["backend"] == "memory"
    assert status["rateLimit"]["enabled"] is True
    assert status["rateLimit"]["backend"] == "memory"
    assert status["idempotency"]["enabled"] is True
    assert status["errorRedaction"]["enabled"] is True
    assert "password" not in str(status).lower()


def _register_and_login(client: TestClient, prefix: str) -> dict:
    email = f"{prefix}@example.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "username": prefix, "password": "password123"},
    )
    return client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()


def _auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


def test_login_rate_limit_returns_429() -> None:
    reset_security_state()
    client = TestClient(app)

    for index in range(6):
        response = client.post("/api/auth/login", json={"email": f"missing-{index}@example.com", "password": "bad"})

    assert response.status_code == 429
    assert "too many" in response.text.lower()


def test_rag_upload_rate_limit_returns_429() -> None:
    reset_security_state()
    client = TestClient(app)
    tokens = _register_and_login(client, "rag_upload_limited")

    for index in range(11):
        response = client.post(
            "/api/rag/documents/upload",
            headers=_auth_headers(tokens),
            data={"title": f"Limited {index}", "knowledgeBase": "role_knowledge", "visibility": "private"},
            files={"file": (f"limited-{index}.txt", b"limited content", "text/plain")},
        )

    assert response.status_code == 429
