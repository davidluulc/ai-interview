from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

from .config import (
    AUTO_INIT_DB,
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_TASK_ALWAYS_EAGER,
    DATABASE_URL,
    REDIS_ENABLED,
    REDIS_URL,
)
from .database import describe_database_url
from .redis_client import build_redis_health, redis_client


def mask_service_url(raw_url: str) -> str:
    raw = str(raw_url or "")
    if raw.startswith("sqlite") or "://" not in raw:
        return raw

    parsed = urlsplit(raw)
    if parsed.password is None:
        return raw

    username = parsed.username or ""
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    userinfo = f"{username}:***@" if username else ":***@"
    netloc = f"{userinfo}{hostname}{port}"
    return urlunsplit(SplitResult(parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def build_infrastructure_status(
    *,
    database_url: str = DATABASE_URL,
    auto_init_db: bool = AUTO_INIT_DB,
    redis_enabled: bool = REDIS_ENABLED,
    redis_url: str = REDIS_URL,
    redis_client: Any | None = redis_client,
    celery_broker_url: str = CELERY_BROKER_URL,
    celery_result_backend: str = CELERY_RESULT_BACKEND,
    celery_task_always_eager: bool = CELERY_TASK_ALWAYS_EAGER,
) -> dict[str, Any]:
    from .celery_app import build_celery_status

    redis_health = build_redis_health(enabled=redis_enabled, redis_url=redis_url, client=redis_client).to_dict()
    redis_health["url"] = mask_service_url(str(redis_health.get("url") or ""))
    return {
        "database": describe_database_url(database_url, auto_init=auto_init_db),
        "redis": redis_health,
        "celery": build_celery_status(
            broker_url=celery_broker_url,
            result_backend=celery_result_backend,
            task_always_eager=celery_task_always_eager,
        ),
    }


def get_infrastructure_status() -> dict[str, Any]:
    return build_infrastructure_status()
