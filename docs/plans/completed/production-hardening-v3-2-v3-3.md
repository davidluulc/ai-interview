# Production Hardening V3.2 + V3.3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend production hardening for token blacklist, rate limiting, error redaction, RAG ingestion idempotency, retry protection, and admin observability while preserving local SQLite and Redis-disabled testability.

**Architecture:** Introduce small, testable services under `backend_python/security.py` and reuse existing Redis cache abstractions with memory fallback. Keep existing APIs compatible by adding optional fields and summaries rather than changing request contracts. Implement backend behavior first with focused pytest coverage, then add minimal Vue type/display updates.

**Tech Stack:** FastAPI, SQLAlchemy, PyJWT, pytest, Redis optional cache wrapper, Vue3, TypeScript, Vitest.

---

## File Structure

- Create: `backend_python/security.py`
  - Token blacklist service, memory fallback store, rate limiter, error redaction helpers, and security status summary.
- Modify: `backend_python/auth.py`
  - Add token jti support or deterministic token hash fallback, blacklist check in `get_current_user`, and blacklist write on logout route integration.
- Modify: `backend_python/routes/auth.py`
  - Apply login rate limit and blacklist current access token on logout.
- Modify: `backend_python/routes/rag_documents.py`
  - Apply upload/retry rate limits, upload idempotency, retry state protection, and 409/429 stable messages.
- Modify: `backend_python/routes/interview.py`
  - Apply next-question rate limit without changing request/response schema.
- Modify: `backend_python/routes/admin.py`
  - Expose security summary and richer RAG ingestion anomaly summary.
- Modify: `backend_python/infrastructure.py`
  - Include security summary in infrastructure/config aggregation if appropriate.
- Modify: `backend_python/llm_client.py`, `backend_python/embedding_client.py`, `backend_python/rerank_client.py`
  - Redact provider-facing error details from external responses while keeping logs useful.
- Modify: `backend_python/rag_ingestion_tasks.py`
  - Add idempotency metadata, retry lock metadata, and failure-stage normalization helpers.
- Modify: backend tests:
  - `tests/test_security_hardening.py`
  - `tests/test_auth.py`
  - `tests/test_admin_routes.py`
  - `tests/test_rag_documents_upload_route.py`
  - `tests/test_interview_agent_route.py`
  - provider client tests if existing coverage needs tightening.
- Modify: frontend:
  - `frontend/src/api/admin.ts`
  - `frontend/src/pages/app/AdminPage.vue`
  - `frontend/src/pages/app/admin-page.test.ts`
  - `frontend/src/stores/knowledge.ts`
  - `frontend/src/pages/app/KnowledgePage.vue`
  - `frontend/src/pages/app/knowledge-page.test.ts`
- Modify docs and archive on completion:
  - `docs/project-baseline.md`
  - `docs/roadmap/current-state.md`
  - `docs/specs/README.md`
  - `docs/plans/README.md`
  - Move active spec/plan to completed only after all V3.2/V3.3 requirements are verified.

---

## Task 1: Security Service Foundation

**Files:**
- Create: `tests/test_security_hardening.py`
- Create: `backend_python/security.py`

- [ ] **Step 1: Write failing tests for memory token blacklist**

Add to `tests/test_security_hardening.py`:

```python
from backend_python.security import MemoryTokenBlacklist, hash_token


def test_memory_token_blacklist_rejects_blacklisted_token() -> None:
    blacklist = MemoryTokenBlacklist()
    token = "access-token-value"

    assert blacklist.contains(hash_token(token)) is False

    blacklist.add(hash_token(token), ttl_seconds=60)

    assert blacklist.contains(hash_token(token)) is True
```

- [ ] **Step 2: Write failing tests for fixed-window rate limiter**

Add:

```python
from backend_python.security import MemoryRateLimitStore, RateLimitRule, RateLimiter


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
```

- [ ] **Step 3: Write failing tests for security status summary**

Add:

```python
from backend_python.security import build_security_status


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
```

- [ ] **Step 4: Run RED tests**

Run:

```powershell
python -m pytest tests/test_security_hardening.py -q
```

Expected: fail because `backend_python.security` does not exist.

- [ ] **Step 5: Implement minimal security service**

Create `backend_python/security.py`:

```python
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from threading import Lock
from typing import Protocol


def hash_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


class TokenBlacklistStore(Protocol):
    def add(self, token_key: str, ttl_seconds: int) -> None: ...
    def contains(self, token_key: str) -> bool: ...


class MemoryTokenBlacklist:
    def __init__(self) -> None:
        self._items: dict[str, float] = {}
        self._lock = Lock()

    def add(self, token_key: str, ttl_seconds: int) -> None:
        expires_at = time.time() + max(int(ttl_seconds), 1)
        with self._lock:
            self._items[token_key] = expires_at

    def contains(self, token_key: str) -> bool:
        now = time.time()
        with self._lock:
            expires_at = self._items.get(token_key)
            if expires_at is None:
                return False
            if expires_at <= now:
                self._items.pop(token_key, None)
                return False
            return True


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class MemoryRateLimitStore:
    def __init__(self) -> None:
        self._items: dict[str, tuple[int, float]] = {}
        self._lock = Lock()

    def hit(self, key: str, *, window_seconds: int) -> tuple[int, int]:
        now = time.time()
        with self._lock:
            count, reset_at = self._items.get(key, (0, now + window_seconds))
            if reset_at <= now:
                count = 0
                reset_at = now + window_seconds
            count += 1
            self._items[key] = (count, reset_at)
            return count, max(int(reset_at - now), 1)


class RateLimiter:
    def __init__(self, *, store: MemoryRateLimitStore, rules: dict[str, RateLimitRule]) -> None:
        self.store = store
        self.rules = rules

    def check(self, rule_name: str, identity: str) -> RateLimitResult:
        rule = self.rules[rule_name]
        count, retry_after = self.store.hit(f"{rule_name}:{identity}", window_seconds=rule.window_seconds)
        remaining = max(rule.limit - count, 0)
        return RateLimitResult(
            allowed=count <= rule.limit,
            limit=rule.limit,
            remaining=remaining,
            retry_after_seconds=retry_after if count > rule.limit else 0,
        )


DEFAULT_RATE_LIMIT_RULES = {
    "auth.login": RateLimitRule(limit=5, window_seconds=60),
    "rag.upload": RateLimitRule(limit=10, window_seconds=60),
    "rag.retry": RateLimitRule(limit=6, window_seconds=60),
    "interview.next_question": RateLimitRule(limit=30, window_seconds=60),
    "report.generate": RateLimitRule(limit=10, window_seconds=60),
}

token_blacklist = MemoryTokenBlacklist()
rate_limiter = RateLimiter(store=MemoryRateLimitStore(), rules=DEFAULT_RATE_LIMIT_RULES)


def build_security_status(
    *,
    token_blacklist_backend: str = "memory",
    rate_limit_backend: str = "memory",
    idempotency_backend: str = "database",
) -> dict:
    return {
        "tokenBlacklist": {"enabled": True, "backend": token_blacklist_backend},
        "rateLimit": {"enabled": True, "backend": rate_limit_backend},
        "idempotency": {"enabled": True, "backend": idempotency_backend},
        "errorRedaction": {"enabled": True},
    }
```

- [ ] **Step 6: Run GREEN tests**

Run:

```powershell
python -m pytest tests/test_security_hardening.py -q
```

Expected: pass.

---

## Task 2: Token Blacklist on Logout and Auth Check

**Files:**
- Modify: `tests/test_auth.py`
- Modify: `backend_python/auth.py`
- Modify: `backend_python/routes/auth.py`

- [ ] **Step 1: Write failing logout blacklist route test**

Add to `tests/test_auth.py`:

```python
def test_logout_blacklists_current_access_token() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "blacklist_access")

    logout_response = client.post("/api/auth/logout", headers=auth_headers(tokens), json={"refreshToken": tokens["refreshToken"]})
    assert logout_response.status_code == 200

    me_response = client.get("/api/auth/me", headers=auth_headers(tokens))
    assert me_response.status_code == 401
```

- [ ] **Step 2: Run RED test**

Run:

```powershell
python -m pytest tests/test_auth.py::test_logout_blacklists_current_access_token -q
```

Expected: fail because old access token still works after logout.

- [ ] **Step 3: Add blacklist check in auth dependency**

In `backend_python/auth.py`, import `hash_token` and `token_blacklist`. In the access-token decoding path used by `get_current_user`, reject blacklisted tokens:

```python
from .security import hash_token, token_blacklist
```

Before accepting the credentials token:

```python
if token_blacklist.contains(hash_token(token)):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked.")
```

- [ ] **Step 4: Blacklist token on logout**

In `backend_python/routes/auth.py`, make logout read the bearer access token through `credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme_or_http_bearer_equivalent)` if the project already exposes a helper. If not, use the existing auth dependency pattern and request header:

```python
authorization = request.headers.get("authorization", "")
if authorization.lower().startswith("bearer "):
    access_token = authorization.split(" ", 1)[1].strip()
    if access_token:
        token_blacklist.add(hash_token(access_token), ttl_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
```

Keep refresh token revocation behavior unchanged.

- [ ] **Step 5: Run GREEN test and auth regression**

Run:

```powershell
python -m pytest tests/test_auth.py -q
```

Expected: pass.

---

## Task 3: Rate Limit Login, RAG Upload/Retry, and Next Question

**Files:**
- Modify: `tests/test_security_hardening.py`
- Modify: `backend_python/security.py`
- Modify: `backend_python/routes/auth.py`
- Modify: `backend_python/routes/rag_documents.py`
- Modify: `backend_python/routes/interview.py`

- [ ] **Step 1: Add failing route-level rate limit tests**

Add to `tests/test_security_hardening.py`:

```python
from fastapi.testclient import TestClient

from backend_python.main import app
from tests.utils import auth_headers, register_and_login


def test_login_rate_limit_returns_429(monkeypatch) -> None:
    client = TestClient(app)
    for index in range(6):
        response = client.post("/api/auth/login", json={"email": f"missing-{index}@example.com", "password": "bad"})
    assert response.status_code == 429
    assert "rate limit" in response.text.lower() or "too many" in response.text.lower()


def test_rag_upload_rate_limit_returns_429(monkeypatch) -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_limited")
    for index in range(11):
        response = client.post(
            "/api/rag/documents/upload",
            headers=auth_headers(tokens),
            data={"title": f"Limited {index}", "knowledgeBase": "role_knowledge", "visibility": "private"},
            files={"file": (f"limited-{index}.txt", b"limited content", "text/plain")},
        )
    assert response.status_code == 429
```

- [ ] **Step 2: Run RED tests**

Run:

```powershell
python -m pytest tests/test_security_hardening.py::test_login_rate_limit_returns_429 tests/test_security_hardening.py::test_rag_upload_rate_limit_returns_429 -q
```

Expected: fail because routes do not apply limiter yet.

- [ ] **Step 3: Add FastAPI helper for rate limit**

In `backend_python/security.py`, add:

```python
from fastapi import HTTPException, Request, status


def client_identity(request: Request, *, user_id: int | None = None) -> str:
    if user_id is not None:
        return f"user:{user_id}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def enforce_rate_limit(rule_name: str, identity: str) -> None:
    result = rate_limiter.check(rule_name, identity)
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please retry later.",
            headers={"Retry-After": str(result.retry_after_seconds)},
        )
```

- [ ] **Step 4: Apply limiter to routes**

Apply:

```python
enforce_rate_limit("auth.login", client_identity(request))
enforce_rate_limit("rag.upload", client_identity(request, user_id=current_user.id))
enforce_rate_limit("rag.retry", client_identity(request, user_id=current_user.id))
enforce_rate_limit("interview.next_question", client_identity(request, user_id=current_user.id))
```

Add `request: Request` parameters where needed without changing request body schemas.

- [ ] **Step 5: Run focused GREEN tests**

Run:

```powershell
python -m pytest tests/test_security_hardening.py -q
```

Expected: pass.

---

## Task 4: Provider Error Redaction

**Files:**
- Modify: provider client tests or create `tests/test_provider_error_redaction.py`
- Modify: `backend_python/security.py`
- Modify: `backend_python/llm_client.py`
- Modify: `backend_python/embedding_client.py`
- Modify: `backend_python/rerank_client.py`

- [ ] **Step 1: Write failing redaction helper test**

Create `tests/test_provider_error_redaction.py`:

```python
from backend_python.security import redact_error_detail


def test_redact_error_detail_removes_sensitive_values() -> None:
    message = "failed api_key=sk-secret url=sqlite:///C:/private/app.db path=C:/Users/name/project"

    redacted = redact_error_detail(message)

    assert "sk-secret" not in redacted
    assert "sqlite:///" not in redacted
    assert "C:/Users" not in redacted
```

- [ ] **Step 2: Run RED test**

Run:

```powershell
python -m pytest tests/test_provider_error_redaction.py -q
```

Expected: fail because helper does not exist.

- [ ] **Step 3: Implement redaction helper**

In `backend_python/security.py`, add:

```python
import re


def redact_error_detail(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED_API_KEY]", text)
    text = re.sub(r"(sqlite|postgresql|mysql)(\\+\\w+)?://[^\\s]+", "[REDACTED_DATABASE_URL]", text)
    text = re.sub(r"[A-Za-z]:[/\\\\][^\\s]+", "[REDACTED_PATH]", text)
    return text[:500]
```

- [ ] **Step 4: Tighten provider public errors**

Update provider clients so external `HTTPException.detail` remains stable:

```python
raise HTTPException(status_code=502, detail="Embedding provider request failed.")
raise HTTPException(status_code=502, detail="Rerank provider request failed.")
raise HTTPException(status_code=504, detail="External provider request timed out.")
```

Keep detailed info only in logs, passed through `redact_error_detail`.

- [ ] **Step 5: Run provider tests**

Run:

```powershell
python -m pytest tests/test_provider_error_redaction.py tests/test_embedding_client.py tests/test_rerank_client.py -q
```

Expected: pass.

---

## Task 5: RAG Upload Idempotency

**Files:**
- Modify: `tests/test_rag_documents_upload_route.py`
- Modify: `backend_python/rag_ingestion_tasks.py`
- Modify: `backend_python/routes/rag_documents.py`

- [ ] **Step 1: Write failing duplicate upload test**

Add to `tests/test_rag_documents_upload_route.py`:

```python
def test_upload_same_file_returns_existing_ingestion_task(monkeypatch) -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_upload_idempotent")

    payload = {
        "title": "Idempotent Upload",
        "knowledgeBase": "role_knowledge",
        "visibility": "private",
    }
    first = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data=payload,
        files={"file": ("same.txt", b"same idempotent content", "text/plain")},
    )
    second = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data=payload,
        files={"file": ("same.txt", b"same idempotent content", "text/plain")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["taskId"] == first.json()["taskId"]
    assert second.json()["idempotencyHit"] is True
```

- [ ] **Step 2: Run RED test**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py::test_upload_same_file_returns_existing_ingestion_task -q
```

Expected: fail because duplicate upload creates a new task or lacks `idempotencyHit`.

- [ ] **Step 3: Implement idempotency key helpers**

In `backend_python/rag_ingestion_tasks.py`, add:

```python
def build_ingestion_idempotency_key(*, user_id: int, knowledge_base: str, title: str, content_hash: str) -> str:
    raw = f"{user_id}:{knowledge_base}:{title.strip().lower()}:{content_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

Add helpers to merge `idempotencyKey` / `idempotencyHit` into `result_json`, and a lookup function scanning recent tasks for same user and key.

- [ ] **Step 4: Apply upload idempotency in route**

In upload route:

1. Parse file and compute content hash before creating task.
2. Build idempotency key.
3. If an existing task for current user has same idempotency key and status in `pending/queued/running/succeeded/failed`, return serialized existing task with `idempotencyHit=True`.
4. New task stores `idempotencyKey` and `idempotencyHit=False`.

- [ ] **Step 5: Serialize idempotency fields**

In `serialize_ingestion_task()`, include:

```python
"idempotencyKey": result.get("idempotencyKey", ""),
"idempotencyHit": bool(result.get("idempotencyHit", False)),
```

- [ ] **Step 6: Run GREEN upload route tests**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py -q
```

Expected: pass.

---

## Task 6: Retry State Protection and Lock Metadata

**Files:**
- Modify: `tests/test_rag_documents_upload_route.py`
- Modify: `backend_python/routes/rag_documents.py`
- Modify: `backend_python/rag_ingestion_tasks.py`

- [ ] **Step 1: Write failing retry conflict test**

Add:

```python
def test_retry_running_ingestion_task_returns_409() -> None:
    client = TestClient(app)
    tokens = register_and_login(client, "rag_retry_conflict")
    upload = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers(tokens),
        data={"title": "Retry Conflict", "knowledgeBase": "role_knowledge", "visibility": "private"},
        files={"file": ("retry-conflict.txt", b"retry conflict content", "text/plain")},
    )
    task_id = upload.json()["taskId"]

    with SessionLocal() as db:
        task = db.scalar(select(RagIngestionTask).where(RagIngestionTask.task_id == task_id))
        assert task is not None
        task.status = "running"
        task.can_retry = 1
        db.add(task)
        db.commit()

    response = client.post(f"/api/rag/documents/ingestion-tasks/{task_id}/retry", headers=auth_headers(tokens))

    assert response.status_code == 409
    assert "already" in response.text.lower() or "processing" in response.text.lower()
```

- [ ] **Step 2: Run RED/GREEN focused test**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py::test_retry_running_ingestion_task_returns_409 -q
```

If already passes, add assertion that failed retry writes no additional dispatch metadata. If it fails, update retry route to return 409 for queued/running before incrementing retry count.

- [ ] **Step 3: Add retry lock metadata on successful retry**

When retry is accepted, write:

```python
merge_ingestion_task_result(db, task, {"retryLockedAt": datetime.now(UTC).isoformat()})
```

- [ ] **Step 4: Assert retry lock metadata**

Extend existing retry success test:

```python
assert body["retryLockedAt"]
```

Update serializer to include `retryLockedAt`.

- [ ] **Step 5: Run route tests**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py -q
```

Expected: pass.

---

## Task 7: Admin Security Summary and Ingestion Anomaly Aggregation

**Files:**
- Modify: `tests/test_admin_routes.py`
- Modify: `backend_python/routes/admin.py`
- Modify: `backend_python/infrastructure.py`

- [ ] **Step 1: Write failing admin config security summary test**

Add to `tests/test_admin_routes.py`:

```python
def test_admin_config_exposes_security_summary_without_secrets() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"admin-security-{suffix}@example.com"
    register_and_login(client, email, f"admin_security_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    response = client.get("/api/admin/config", headers={"Authorization": f"Bearer {admin['accessToken']}"})

    assert response.status_code == 200
    body = response.json()
    assert body["security"]["tokenBlacklist"]["enabled"] is True
    assert body["security"]["rateLimit"]["enabled"] is True
    assert body["security"]["idempotency"]["enabled"] is True
    assert "password" not in str(body).lower()
```

- [ ] **Step 2: Write failing anomaly aggregation test**

Add:

```python
def test_admin_rag_ingestion_tasks_include_failure_stage_summary() -> None:
    client = TestClient(app)
    suffix = uuid4().hex
    email = f"admin-ingestion-stage-{suffix}@example.com"
    register_and_login(client, email, f"admin_ingestion_stage_{suffix[:8]}")
    promote_to_admin(email)
    admin = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        task = RagIngestionTask(
            task_id=f"rag_ingestion-stage-{suffix}",
            user_id=user.id,
            title="Stage failure",
            original_filename="stage.md",
            knowledge_base="role_knowledge",
            status="failed",
            error_message="Embedding provider request failed.",
            result_json='{"failureStage":"embedding","durationMs":1234}',
            can_retry=1,
        )
        db.add(task)
        db.commit()

    response = client.get("/api/admin/rag/ingestion-tasks", headers={"Authorization": f"Bearer {admin['accessToken']}"})

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["failureStages"]["embedding"] >= 1
    assert body["summary"]["maxDurationMs"] >= 1234
```

- [ ] **Step 3: Run RED tests**

Run:

```powershell
python -m pytest tests/test_admin_routes.py::test_admin_config_exposes_security_summary_without_secrets tests/test_admin_routes.py::test_admin_rag_ingestion_tasks_include_failure_stage_summary -q
```

Expected: fail because security and aggregation fields are missing.

- [ ] **Step 4: Add security summary to admin config**

In `backend_python/routes/admin.py`, include:

```python
from ..security import build_security_status

...
"security": build_security_status(),
```

- [ ] **Step 5: Add ingestion summary fields**

In admin ingestion task summary builder, add:

```python
failureStages: dict[str, int]
averageDurationMs: int
maxDurationMs: int
idempotencyHitCount: int
```

Read these from each task `result_json`.

- [ ] **Step 6: Run GREEN tests**

Run:

```powershell
python -m pytest tests/test_admin_routes.py -q
```

Expected: pass.

---

## Task 8: Minimal Frontend Display

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/pages/app/AdminPage.vue`
- Modify: `frontend/src/pages/app/admin-page.test.ts`
- Modify: `frontend/src/api/knowledge.ts`
- Modify: `frontend/src/stores/knowledge.ts`
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
- Modify: `frontend/src/pages/app/knowledge-page.test.ts`

- [ ] **Step 1: Update admin page test first**

In `frontend/src/pages/app/admin-page.test.ts`, extend mocked config:

```ts
security: {
  tokenBlacklist: { enabled: true, backend: "memory" },
  rateLimit: { enabled: true, backend: "memory" },
  idempotency: { enabled: true, backend: "database" },
  errorRedaction: { enabled: true }
}
```

Extend mocked ingestion summary:

```ts
failureStages: { embedding: 1 },
averageDurationMs: 800,
maxDurationMs: 1234,
idempotencyHitCount: 2
```

Assert:

```ts
expect(wrapper.text()).toContain("安全与流量保护");
expect(wrapper.text()).toContain("Token blacklist");
expect(wrapper.text()).toContain("限流");
expect(wrapper.text()).toContain("幂等");
expect(wrapper.text()).toContain("embedding");
expect(wrapper.text()).toContain("最长耗时");
```

- [ ] **Step 2: Run RED frontend test**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts
```

Expected: fail because display is missing.

- [ ] **Step 3: Add frontend types**

In `frontend/src/api/admin.ts`, add optional `security` fields to `AdminConfig` and ingestion summary fields to existing types.

- [ ] **Step 4: Add minimal admin display**

In `AdminPage.vue`, add a compact section under system config or infrastructure status:

```vue
<p><span>Token blacklist</span><strong>{{ securitySummary.tokenBlacklist }}</strong></p>
<p><span>限流</span><strong>{{ securitySummary.rateLimit }}</strong></p>
<p><span>幂等</span><strong>{{ securitySummary.idempotency }}</strong></p>
```

Add ingestion anomaly rows near RAG ingestion monitor:

```vue
<span>最长耗时 {{ admin.ragIngestionTasks.summary.maxDurationMs || 0 }}ms</span>
<span>幂等命中 {{ admin.ragIngestionTasks.summary.idempotencyHitCount || 0 }}</span>
```

- [ ] **Step 5: Add knowledge page 409/429 test**

In `knowledge-page.test.ts`, mock upload/retry store error with a 429/409 message and assert visible text is understandable:

```ts
knowledgeStore.uploadError = "请求过于频繁，请稍后重试。";
expect(wrapper.text()).toContain("请求过于频繁");
```

- [ ] **Step 6: Run frontend focused tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/admin-page.test.ts src/pages/app/knowledge-page.test.ts
```

Expected: pass.

---

## Task 9: Documentation, Archival, and Verification

**Files:**
- Modify: `docs/project-baseline.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`
- Move: `docs/specs/active/production-hardening-v3-2-v3-3-design.md`
- Move: `docs/plans/active/production-hardening-v3-2-v3-3.md`

- [ ] **Step 1: Update docs after implementation**

Record:

```text
Production Hardening V3.2 + V3.3 已完成：系统新增 token blacklist、基础限流、错误脱敏、RAG upload 幂等、retry 并发保护、任务异常聚合和管理员安全摘要。SQLite 仍是本地默认数据库，Redis 保持 disabled/memory fallback 可测路径，未做 Docker/Nginx/VPS/HTTPS 上线。
```

- [ ] **Step 2: Archive spec and plan**

Move:

```powershell
Move-Item -LiteralPath docs/specs/active/production-hardening-v3-2-v3-3-design.md -Destination docs/specs/completed/production-hardening-v3-2-v3-3-design.md
Move-Item -LiteralPath docs/plans/active/production-hardening-v3-2-v3-3.md -Destination docs/plans/completed/production-hardening-v3-2-v3-3.md
```

- [ ] **Step 3: Full backend verification**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 4: Full frontend verification**

Run:

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

Expected: all tests pass and build succeeds.

- [ ] **Step 5: Browser verification**

Verify with in-app browser:

```text
http://127.0.0.1:5173/vue/app/knowledge
http://127.0.0.1:5173/vue/app/admin
```

Check desktop and mobile:

- No `undefined`.
- No horizontal overflow.
- Admin shows security/rate limit/idempotency summary.
- Admin shows ingestion anomaly fields.
- Knowledge page keeps upload/retry status readable.

- [ ] **Step 6: Final scope audit**

Run:

```powershell
git status --short
git diff --stat
```

Confirm no Docker/Nginx/VPS/HTTPS, Qdrant/pgvector/object storage, OCR/Word/Excel/web parsing, RAG algorithm rewrite, or Agent/LangGraph mainline rewrite.

---

## Self-Review

Spec coverage:

- Token blacklist: Tasks 1-2 and 7-8.
- Rate limiting: Tasks 1 and 3, frontend message in Task 8.
- Error redaction: Task 4.
- Admin permission boundary: covered by existing admin tests plus Task 7; add more explicit 403 tests during execution if gaps are found.
- RAG upload idempotency: Task 5.
- Retry state protection: Task 6.
- Task anomaly aggregation: Task 7.
- Minimal frontend: Task 8.
- Full verification and browser: Task 9.

Known boundaries:

- Redis backend implementation can remain memory fallback if no Redis service is available; the public interface must not require real Redis for tests.
- PostgreSQL/Docker/Nginx/VPS/HTTPS and RAG/Agent/LangGraph rewrites are out of scope.
