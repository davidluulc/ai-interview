from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

_TASKS: dict[str, dict] = {}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_task_status(*, task_type: str, message: str = "Task created.") -> dict:
    now = utc_now_iso()
    task_id = f"{task_type}-{uuid4().hex}"
    task = {
        "taskId": task_id,
        "taskType": task_type,
        "status": "pending",
        "progress": 0,
        "message": message,
        "result": {},
        "error": "",
        "createdAt": now,
        "updatedAt": now,
    }
    _TASKS[task_id] = task
    return deepcopy(task)


def get_task_status(task_id: str) -> dict:
    task = _TASKS.get(str(task_id or ""))
    if not task:
        return {}
    return deepcopy(task)


def update_task_status(
    task_id: str,
    *,
    status: str,
    progress: int,
    message: str = "",
    result: dict | None = None,
    error: str = "",
) -> dict:
    if task_id not in _TASKS:
        raise KeyError(f"Task not found: {task_id}")
    task = _TASKS[task_id]
    task["status"] = status
    task["progress"] = max(0, min(int(progress), 100))
    if message:
        task["message"] = message
    if result is not None:
        task["result"] = result
    task["error"] = error
    task["updatedAt"] = utc_now_iso()
    return deepcopy(task)


def succeed_task_status(task_id: str, *, result: dict, message: str = "Task finished.") -> dict:
    return update_task_status(task_id, status="success", progress=100, message=message, result=result, error="")


def fail_task_status(task_id: str, *, error: str, message: str = "Task failed.") -> dict:
    return update_task_status(task_id, status="failed", progress=100, message=message, error=error)
