from fastapi.testclient import TestClient

from backend_python.main import app
from backend_python.task_status import (
    create_task_status,
    fail_task_status,
    get_task_status,
    succeed_task_status,
)


def test_task_status_lifecycle() -> None:
    task = create_task_status(task_type="rag_evaluation")

    assert task["status"] == "pending"
    assert task["taskType"] == "rag_evaluation"

    succeed_task_status(task["taskId"], result={"caseCount": 1})
    done = get_task_status(task["taskId"])
    assert done["status"] == "success"
    assert done["progress"] == 100
    assert done["result"] == {"caseCount": 1}


def test_task_status_records_failure() -> None:
    task = create_task_status(task_type="rag_evaluation")

    fail_task_status(task["taskId"], error="boom")
    failed = get_task_status(task["taskId"])

    assert failed["status"] == "failed"
    assert failed["error"] == "boom"


def test_rag_evaluation_async_task_routes_return_status() -> None:
    client = TestClient(app)

    response = client.post("/api/rag/evaluation/tasks", json={"modes": ["bm25"], "k": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["taskType"] == "rag_evaluation"
    assert payload["taskId"]
    assert payload["status"] in {"pending", "running", "success"}

    status_response = client.get(f"/api/rag/evaluation/tasks/{payload['taskId']}")

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["taskId"] == payload["taskId"]
    assert status_payload["taskType"] == "rag_evaluation"
