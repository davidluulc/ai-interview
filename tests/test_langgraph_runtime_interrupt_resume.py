from fastapi.testclient import TestClient

from backend_python.main import app


def test_langgraph_runtime_run_can_interrupt() -> None:
    client = TestClient(app)
    payload = {
        "threadId": "runtime-interrupt-1",
        "agentRuntime": "langgraph",
        "agentMode": "coach",
        "history": [{"answer": "不会"}, {"answer": "不知道"}, {"answer": "还是不会"}],
        "answer": "不会",
        "nextStage": "技术追问",
        "enableInterrupt": True,
    }

    response = client.post("/api/langgraph-agent/runtime/run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["threadId"] == "runtime-interrupt-1"
    assert data["runtime"] == "langgraph"
    assert data["status"] == "interrupted"
    assert data["interrupt"]["options"]
    assert data["checkpointSummary"]["requiresHumanReview"] is True


def test_langgraph_runtime_resume_uses_existing_thread() -> None:
    client = TestClient(app)
    client.post(
        "/api/langgraph-agent/runtime/run",
        json={
            "threadId": "runtime-resume-1",
            "agentRuntime": "langgraph",
            "history": [{"answer": "不会"}, {"answer": "不知道"}, {"answer": "不会"}],
            "answer": "不会",
            "enableInterrupt": True,
        },
    )

    response = client.post(
        "/api/langgraph-agent/runtime/resume",
        json={
            "threadId": "runtime-resume-1",
            "decision": "switch_to_coach",
            "comment": "先进入学习辅导",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["threadId"] == "runtime-resume-1"
    assert data["status"] == "completed"
    assert data["resumeDecision"] == "switch_to_coach"
    assert data["checkpointSummary"]["resumeDecision"] == "switch_to_coach"


def test_langgraph_runtime_resume_missing_thread_returns_404() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/langgraph-agent/runtime/resume",
        json={"threadId": "missing-runtime-thread", "decision": "continue_interview"},
    )

    assert response.status_code == 404


def test_langgraph_runtime_runs_endpoint_lists_thread_runs() -> None:
    client = TestClient(app)
    payload = {
        "threadId": "route-runtime-runs",
        "agentRuntime": "langgraph",
        "answer": "我不知道 checkpoint 是什么",
        "agentMode": "coach",
    }

    run_response = client.post("/api/langgraph-agent/runtime/run", json=payload)
    assert run_response.status_code == 200

    runs_response = client.get("/api/langgraph-agent/runtime/runs/route-runtime-runs")

    assert runs_response.status_code == 200
    body = runs_response.json()
    assert body["threadId"] == "route-runtime-runs"
    assert len(body["items"]) >= 1
    assert body["items"][0]["threadId"] == "route-runtime-runs"
    assert "runtime" in body["items"][0]
