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


def build_worker_readiness(
    *,
    broker_url: str,
    result_backend: str,
    task_always_eager: bool,
) -> dict:
    missing_requirements: list[str] = []
    if not str(broker_url or "").strip():
        missing_requirements.append("broker_url")
    if not str(result_backend or "").strip():
        missing_requirements.append("result_backend")

    if task_always_eager:
        return {
            "mode": "eager",
            "readyForWorker": False,
            "requiresExternalWorker": False,
            "missingRequirements": [],
            "message": "当前为 eager/test 模式，任务会在请求进程内同步执行，不需要外部 Celery worker。",
        }

    ready_for_worker = not missing_requirements
    return {
        "mode": "worker",
        "readyForWorker": ready_for_worker,
        "requiresExternalWorker": True,
        "missingRequirements": missing_requirements,
        "message": (
            "Celery worker 模式已具备 broker/result backend 配置，需要单独启动 Celery worker。"
            if ready_for_worker
            else "Celery worker 模式缺少必要配置，任务无法稳定进入外部队列。"
        ),
    }


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
        "workerReadiness": build_worker_readiness(
            broker_url=broker_url,
            result_backend=result_backend,
            task_always_eager=task_always_eager,
        ),
    }
