from backend_python.infrastructure import build_infrastructure_status


def test_build_infrastructure_status_combines_database_redis_and_celery() -> None:
    status = build_infrastructure_status(
        database_url="postgresql+psycopg://app:db-secret@db:5432/app",
        auto_init_db=True,
        redis_enabled=True,
        redis_url="redis://:redis-secret@redis:6379/0",
        redis_client=None,
        celery_broker_url="redis://:broker-secret@redis:6379/1",
        celery_result_backend="redis://:result-secret@redis:6379/2",
        celery_task_always_eager=False,
    )

    assert status["database"]["dialect"] == "postgresql+psycopg"
    assert status["database"]["autoInitEnabled"] is False
    assert status["redis"]["status"] == "error"
    assert status["redis"]["url"] == "redis://:***@redis:6379/0"
    assert status["celery"]["status"] == "configured"
    assert "db-secret" not in str(status)
    assert "redis-secret" not in str(status)
    assert "broker-secret" not in str(status)
    assert "result-secret" not in str(status)
