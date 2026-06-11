from backend_python.celery_app import celery_app
from backend_python.task_status import fail_task_status, succeed_task_status, update_task_status


@celery_app.task(name="backend_python.tasks.rag_evaluation.run_rag_evaluation_task")
def run_rag_evaluation_task(task_id: str, modes: list[str] | None = None, k: int = 3) -> dict:
    safe_modes = [str(mode) for mode in (modes or ["bm25"]) if str(mode).strip()]
    if not safe_modes:
        safe_modes = ["bm25"]
    safe_k = max(1, min(int(k or 3), 10))
    try:
        update_task_status(
            task_id,
            status="running",
            progress=30,
            message="RAG evaluation task is running.",
        )
        result = {
            "caseCount": 0,
            "modes": safe_modes,
            "k": safe_k,
            "note": "Async RAG evaluation task scaffold is ready; full batch evaluation can reuse existing rag_evaluation service.",
        }
        return succeed_task_status(task_id, result=result, message="RAG evaluation task finished.")
    except Exception as exc:
        return fail_task_status(task_id, error=str(exc))
