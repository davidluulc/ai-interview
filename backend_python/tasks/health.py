from backend_python.celery_app import celery_app


@celery_app.task(name="backend_python.tasks.health.ping_task")
def ping_task() -> dict:
    return {"status": "ok", "task": "ping"}
