from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from fastapi import HTTPException, Request, status


def hash_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def redact_error_detail(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED_API_KEY]", text)
    text = re.sub(r"(sqlite|postgresql|mysql)(\+\w+)?://[^\s]+", "[REDACTED_DATABASE_URL]", text)
    text = re.sub(r"[A-Za-z]:[/\\][^\s]+", "[REDACTED_PATH]", text)
    return text[:500]


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

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


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

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


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
rate_limit_store = MemoryRateLimitStore()
rate_limiter = RateLimiter(store=rate_limit_store, rules=DEFAULT_RATE_LIMIT_RULES)


def reset_security_state() -> None:
    token_blacklist.clear()
    rate_limit_store.clear()


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
