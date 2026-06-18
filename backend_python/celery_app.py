from celery import Celery

from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_TASK_ALWAYS_EAGER
from .database import mask_database_url

CELERY_IMPORTS = (
    "backend_python.tasks.health",
    "backend_python.tasks.rag_evaluation",
    "backend_python.tasks.rag_ingestion",
)

CELERY_WORKER_COMMAND = "celery -A backend_python.celery_app.celery_app worker --loglevel=info --pool=solo"


celery_app = Celery(
    "ai_interview",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_always_eager=CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    imports=CELERY_IMPORTS,
    broker_connection_retry_on_startup=True,
)


def build_celery_status(
    *,
    broker_url: str = CELERY_BROKER_URL,
    result_backend: str = CELERY_RESULT_BACKEND,
    task_always_eager: bool = CELERY_TASK_ALWAYS_EAGER,
) -> dict:
    mode = "eager" if task_always_eager else "worker"
    return {
        "status": "eager" if task_always_eager else "configured",
        "mode": mode,
        "taskAlwaysEager": bool(task_always_eager),
        "workerRequired": not bool(task_always_eager),
        "workerCommand": CELERY_WORKER_COMMAND,
        "brokerConfigured": bool(str(broker_url or "").strip()),
        "resultBackendConfigured": bool(str(result_backend or "").strip()),
        "brokerUrl": mask_database_url(broker_url),
        "resultBackend": mask_database_url(result_backend),
        "healthTask": "backend_python.tasks.health.ping_task",
        "registeredTaskModules": list(CELERY_IMPORTS),
    }
