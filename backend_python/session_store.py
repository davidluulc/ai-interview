from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Protocol

from .redis_client import redis_client


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStore(Protocol):
    def create_session(self, *, user_id: int, refresh_token_id: int, ttl_seconds: int) -> str: ...

    def get_session(self, session_id: str) -> dict[str, Any] | None: ...

    def find_active_session_by_refresh_token(self, refresh_token_id: int) -> dict[str, Any] | None: ...

    def touch_session(self, session_id: str, ttl_seconds: int) -> None: ...

    def revoke_session(self, session_id: str, reason: str = "") -> bool: ...

    def revoke_user_sessions(self, user_id: int, reason: str = "") -> int: ...

    def clear(self) -> None: ...


class MemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._user_sessions: dict[int, set[str]] = {}
        self._lock = Lock()

    def create_session(self, *, user_id: int, refresh_token_id: int, ttl_seconds: int) -> str:
        session_id = secrets.token_urlsafe(32)
        record = {
            "sessionId": session_id,
            "userId": user_id,
            "refreshTokenId": refresh_token_id,
            "status": "active",
            "createdAt": utc_iso(),
            "lastSeenAt": utc_iso(),
            "revokedReason": "",
        }
        with self._lock:
            self._sessions[session_id] = record
            self._user_sessions.setdefault(user_id, set()).add(session_id)
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._sessions.get(session_id)
            return dict(record) if record else None

    def find_active_session_by_refresh_token(self, refresh_token_id: int) -> dict[str, Any] | None:
        with self._lock:
            for record in self._sessions.values():
                if record.get("refreshTokenId") == refresh_token_id and record.get("status") == "active":
                    return dict(record)
        return None

    def touch_session(self, session_id: str, ttl_seconds: int) -> None:
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["lastSeenAt"] = utc_iso()

    def revoke_session(self, session_id: str, reason: str = "") -> bool:
        with self._lock:
            record = self._sessions.get(session_id)
            if not record:
                return False
            record["status"] = "revoked"
            record["revokedReason"] = reason
            record["revokedAt"] = utc_iso()
            return True

    def revoke_user_sessions(self, user_id: int, reason: str = "") -> int:
        with self._lock:
            session_ids = list(self._user_sessions.get(user_id, set()))
        revoked = 0
        for session_id in session_ids:
            if self.revoke_session(session_id, reason):
                revoked += 1
        return revoked

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._user_sessions.clear()


class RedisSessionStore:
    def __init__(self, client: Any) -> None:
        self.client = client

    def create_session(self, *, user_id: int, refresh_token_id: int, ttl_seconds: int) -> str:
        session_id = secrets.token_urlsafe(32)
        record = {
            "sessionId": session_id,
            "userId": user_id,
            "refreshTokenId": refresh_token_id,
            "status": "active",
            "createdAt": utc_iso(),
            "lastSeenAt": utc_iso(),
            "revokedReason": "",
        }
        self.client.set(self._session_key(session_id), json.dumps(record, ensure_ascii=False), ex=ttl_seconds)
        self.client.sadd(self._user_key(user_id), session_id)
        self.client.expire(self._user_key(user_id), ttl_seconds)
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        raw = self.client.get(self._session_key(session_id))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return record if isinstance(record, dict) else None

    def find_active_session_by_refresh_token(self, refresh_token_id: int) -> dict[str, Any] | None:
        # The number of sessions per user is small here; scanning auth:session keys keeps the first version simple.
        for key in self.client.scan_iter(match="auth:session:*"):
            raw = self.client.get(key)
            if not raw:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if record.get("refreshTokenId") == refresh_token_id and record.get("status") == "active":
                return record
        return None

    def touch_session(self, session_id: str, ttl_seconds: int) -> None:
        record = self.get_session(session_id)
        if not record:
            return
        record["lastSeenAt"] = utc_iso()
        self.client.set(self._session_key(session_id), json.dumps(record, ensure_ascii=False), ex=ttl_seconds)
        self.client.expire(self._user_key(int(record.get("userId") or 0)), ttl_seconds)

    def revoke_session(self, session_id: str, reason: str = "") -> bool:
        record = self.get_session(session_id)
        if not record:
            return False
        record["status"] = "revoked"
        record["revokedReason"] = reason
        record["revokedAt"] = utc_iso()
        ttl = self.client.ttl(self._session_key(session_id))
        self.client.set(self._session_key(session_id), json.dumps(record, ensure_ascii=False), ex=max(int(ttl), 60))
        return True

    def revoke_user_sessions(self, user_id: int, reason: str = "") -> int:
        session_ids = self.client.smembers(self._user_key(user_id)) or []
        revoked = 0
        for session_id in session_ids:
            if isinstance(session_id, bytes):
                session_id = session_id.decode("utf-8")
            if self.revoke_session(str(session_id), reason):
                revoked += 1
        return revoked

    def clear(self) -> None:
        for key in self.client.scan_iter(match="auth:session:*"):
            self.client.delete(key)
        for key in self.client.scan_iter(match="auth:user_sessions:*"):
            self.client.delete(key)

    @staticmethod
    def _session_key(session_id: str) -> str:
        return f"auth:session:{session_id}"

    @staticmethod
    def _user_key(user_id: int) -> str:
        return f"auth:user_sessions:{user_id}"


session_store: SessionStore = RedisSessionStore(redis_client) if redis_client is not None else MemorySessionStore()
