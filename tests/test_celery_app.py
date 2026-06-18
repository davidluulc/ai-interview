from backend_python.celery_app import build_celery_status, celery_app
from backend_python.tasks.health import ping_task


def test_celery_app_uses_eager_mode_for_tests() -> None:
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True
    assert "backend_python.tasks.health" in celery_app.conf.imports
    assert "backend_python.tasks.rag_evaluation" in celery_app.conf.imports
    assert "backend_python.tasks.rag_ingestion" in celery_app.conf.imports


def test_ping_task_returns_json_serializable_payload() -> None:
    result = ping_task.delay().get(timeout=5)

    assert result["status"] == "ok"
    assert result["task"] == "ping"


def test_build_celery_status_masks_urls_and_marks_eager_mode() -> None:
    status = build_celery_status(
        broker_url="redis://:broker-secret@localhost:6379/1",
        result_backend="redis://:result-secret@localhost:6379/2",
        task_always_eager=True,
    )

    assert status["status"] == "eager"
    assert status["taskAlwaysEager"] is True
    assert "broker-secret" not in status["brokerUrl"]
    assert "result-secret" not in status["resultBackend"]
    assert status["brokerUrl"] == "redis://:***@localhost:6379/1"
    assert status["resultBackend"] == "redis://:***@localhost:6379/2"
    assert status["healthTask"] == "backend_python.tasks.health.ping_task"


def test_celery_status_exposes_eager_mode_and_worker_command() -> None:
    status = build_celery_status(task_always_eager=True)

    assert status["status"] == "eager"
    assert status["mode"] == "eager"
    assert status["taskAlwaysEager"] is True
    assert status["workerRequired"] is False
    assert "celery" in status["workerCommand"]
    assert "backend_python.celery_app.celery_app" in status["workerCommand"]


def test_celery_status_exposes_worker_mode_when_not_eager() -> None:
    status = build_celery_status(
        broker_url="redis://localhost:6379/1",
        result_backend="redis://localhost:6379/2",
        task_always_eager=False,
    )

    assert status["status"] == "configured"
    assert status["mode"] == "worker"
    assert status["taskAlwaysEager"] is False
    assert status["workerRequired"] is True
    assert status["brokerConfigured"] is True
    assert "backend_python.tasks.rag_ingestion" in status["registeredTaskModules"]


def test_celery_status_exposes_worker_readiness_when_eager() -> None:
    status = build_celery_status(
        broker_url="redis://localhost:6379/1",
        result_backend="redis://localhost:6379/2",
        task_always_eager=True,
    )

    assert status["workerReadiness"]["mode"] == "eager"
    assert status["workerReadiness"]["readyForWorker"] is False
    assert status["workerReadiness"]["requiresExternalWorker"] is False
    assert "当前为 eager/test 模式" in status["workerReadiness"]["message"]
    assert status["workerReadiness"]["missingRequirements"] == []


def test_celery_status_exposes_worker_readiness_when_worker_configured() -> None:
    status = build_celery_status(
        broker_url="redis://localhost:6379/1",
        result_backend="redis://localhost:6379/2",
        task_always_eager=False,
    )

    assert status["workerReadiness"]["mode"] == "worker"
    assert status["workerReadiness"]["readyForWorker"] is True
    assert status["workerReadiness"]["requiresExternalWorker"] is True
    assert status["workerReadiness"]["missingRequirements"] == []
    assert "Celery worker" in status["workerReadiness"]["message"]


def test_celery_status_exposes_missing_worker_requirements() -> None:
    status = build_celery_status(
        broker_url="",
        result_backend="",
        task_always_eager=False,
    )

    assert status["workerReadiness"]["mode"] == "worker"
    assert status["workerReadiness"]["readyForWorker"] is False
    assert "broker_url" in status["workerReadiness"]["missingRequirements"]
    assert "result_backend" in status["workerReadiness"]["missingRequirements"]
