from backend_python.celery_app import celery_app
from backend_python.rag_ingestion_tasks import execute_rag_ingestion_task


@celery_app.task(name="backend_python.tasks.rag_ingestion.run_rag_ingestion_task")
def run_rag_ingestion_task(task_id: str) -> dict:
    return execute_rag_ingestion_task(task_id)
