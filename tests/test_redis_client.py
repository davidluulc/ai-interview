from backend_python.redis_client import DisabledRedisCache, RedisHealth, build_redis_health


def test_disabled_redis_cache_is_safe_noop() -> None:
    cache = DisabledRedisCache()

    assert cache.enabled is False
    assert cache.get("missing") is None
    assert cache.set("key", "value", ex=60) is False
    assert cache.exists("key") is False
    assert cache.delete("key") is False


def test_build_redis_health_disabled() -> None:
    health = build_redis_health(enabled=False, redis_url="redis://localhost:6379/0", client=None)

    assert isinstance(health, RedisHealth)
    assert health.status == "disabled"
    assert health.enabled is False
    assert health.url == "redis://localhost:6379/0"


def test_build_redis_health_reports_ping_error() -> None:
    class BrokenClient:
        def ping(self) -> None:
            raise RuntimeError("connection refused")

    health = build_redis_health(enabled=True, redis_url="redis://localhost:6379/0", client=BrokenClient())

    assert health.enabled is True
    assert health.status == "error"
    assert "connection refused" in health.error


def test_build_redis_health_reports_ok_after_successful_ping() -> None:
    class HealthyClient:
        def ping(self) -> bool:
            return True

    health = build_redis_health(enabled=True, redis_url="redis://:secret@localhost:6379/0", client=HealthyClient())

    assert health.enabled is True
    assert health.status == "ok"
    assert health.url == "redis://:secret@localhost:6379/0"
    assert health.error == ""


def test_build_redis_health_enabled_without_client_is_error() -> None:
    health = build_redis_health(enabled=True, redis_url="redis://localhost:6379/0", client=None)

    assert health.enabled is True
    assert health.status == "error"
    assert "not configured" in health.error.lower()
