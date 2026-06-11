from backend_python.celery_app import celery_app
from backend_python.tasks.health import ping_task


def test_celery_app_uses_eager_mode_for_tests() -> None:
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True


def test_ping_task_returns_json_serializable_payload() -> None:
    result = ping_task.delay().get(timeout=5)

    assert result["status"] == "ok"
    assert result["task"] == "ping"
