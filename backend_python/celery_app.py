from celery import Celery

from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_TASK_ALWAYS_EAGER


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
    imports=(
        "backend_python.tasks.health",
        "backend_python.tasks.rag_evaluation",
    ),
    broker_connection_retry_on_startup=True,
)
