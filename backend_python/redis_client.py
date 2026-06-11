from dataclasses import asdict, dataclass
from typing import Any

from .config import REDIS_ENABLED, REDIS_URL


@dataclass
class RedisHealth:
    enabled: bool
    status: str
    url: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DisabledRedisCache:
    enabled = False

    def get(self, key: str) -> None:
        return None

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        return False

    def delete(self, key: str) -> bool:
        return False

    def exists(self, key: str) -> bool:
        return False


class RedisCache:
    enabled = True

    def __init__(self, client: Any) -> None:
        self.client = client

    def get(self, key: str) -> str | None:
        value = self.client.get(key)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        return bool(self.client.set(key, value, ex=ex))

    def delete(self, key: str) -> bool:
        return bool(self.client.delete(key))

    def exists(self, key: str) -> bool:
        return bool(self.client.exists(key))


def build_redis_health(*, enabled: bool, redis_url: str, client: Any | None) -> RedisHealth:
    if not enabled:
        return RedisHealth(enabled=False, status="disabled", url=redis_url)
    if client is None:
        return RedisHealth(
            enabled=True,
            status="unconfigured",
            url=redis_url,
            error="Redis client is not configured.",
        )
    try:
        client.ping()
        return RedisHealth(enabled=True, status="ok", url=redis_url)
    except Exception as exc:
        return RedisHealth(enabled=True, status="error", url=redis_url, error=str(exc))


def create_redis_client(*, enabled: bool = REDIS_ENABLED, redis_url: str = REDIS_URL) -> Any | None:
    if not enabled:
        return None
    try:
        import redis
    except Exception:
        return None
    return redis.Redis.from_url(redis_url, decode_responses=True)


redis_client = create_redis_client()
redis_cache = RedisCache(redis_client) if redis_client is not None else DisabledRedisCache()


def get_redis_health() -> dict[str, Any]:
    return build_redis_health(enabled=REDIS_ENABLED, redis_url=REDIS_URL, client=redis_client).to_dict()
