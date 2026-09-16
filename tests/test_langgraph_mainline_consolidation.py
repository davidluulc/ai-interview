import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from backend_python.main import app
from backend_python.agent_runtime import normalize_agent_runtime
from backend_python.agent_runtime import run_agent_runtime
from backend_python.runtime_policy import decide_runtime_policy


def test_missing_runtime_defaults_to_langgraph_agent_v3_for_user() -> None:
    policy = decide_runtime_policy(
        requested_runtime=None,
        user_role="user",
        agent_mode="coach",
    )

    assert policy["requestedRuntime"] == "langgraph_agent_v3"
    assert policy["allowedRuntime"] == "langgraph_agent_v3"
    assert policy["fallbackRuntime"] == "classic"
    assert policy["visibleRuntimeOnSuccess"] == "langgraph_agent_v3"
    assert policy["visibleRuntimeOnFailure"] == "classic"
    assert policy["canUseLangGraph"] is True


def test_normalize_agent_runtime_defaults_to_v3_and_keeps_mainline_rollback() -> None:
    assert normalize_agent_runtime(None) == "langgraph_agent_v3"
    assert normalize_agent_runtime("") == "langgraph_agent_v3"
    assert normalize_agent_runtime("langgraph_mainline") == "langgraph_mainline"
    assert normalize_agent_runtime("langgraph_agent_v3") == "langgraph_agent_v3"
    assert normalize_agent_runtime("unknown") == "langgraph_agent_v3"


def test_run_agent_runtime_mainline_uses_langgraph_when_quality_passes() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"prompt": "classic fallback question", "stage": "classic", "focus": "fallback"},
            "decision": {"nextAction": "deepen", "difficulty": "medium"},
            "status": "completed",
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {
                "prompt": "langgraph mainline question",
                "content": "langgraph mainline question",
                "stage": "technical_follow_up",
                "focus": "LangGraph",
            },
            "decision": {"nextAction": "deepen", "difficulty": "medium", "reason": "mainline"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"], "currentNode": "update_memory"},
            "runtimeTrace": [{"node": "observe_state"}, {"node": "retrieve_context"}],
            "status": "completed",
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_mainline",
            thread_id="thread-mainline-pass",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"recentQuestions": []},
        )
    )

    assert result["visibleRuntime"] == "langgraph_mainline"
    assert result["question"]["prompt"] == "langgraph mainline question"
    assert result["fallbackRuntime"] == ""
    assert result["runtimeAudit"]["fallbackUsed"] is False


def test_run_agent_runtime_mainline_falls_back_to_classic_when_langgraph_fails() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"prompt": "classic fallback question", "stage": "fallback", "focus": "stability"},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "status": "completed",
        }

    async def langgraph_runner(**kwargs):
        raise RuntimeError("graph exploded")

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_mainline",
            thread_id="thread-mainline-fallback",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"recentQuestions": []},
        )
    )

    assert result["visibleRuntime"] == "classic"
    assert result["question"]["prompt"] == "classic fallback question"
    assert result["fallbackRuntime"] == "classic"
    assert result["runtimeAudit"]["fallbackUsed"] is True
    assert "LangGraph runtime 执行失败" in result["runtimeAudit"]["qualityGateReasons"]


def test_next_question_defaults_to_langgraph_agent_v3(monkeypatch) -> None:
    from backend_python.routes import interview

    captured = {}

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "deepen",
                "stage": "technical_follow_up",
                "difficulty": "medium",
                "focus": "LangGraph workflow",
                "reason": "classic decision setup",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "technical_follow_up",
            "stability": "dynamic",
            "focus": "LangGraph workflow",
            "prompt": "classic setup question",
        }

    async def fake_run_agent_runtime(**kwargs):
        captured["agent_runtime"] = kwargs["agent_runtime"]
        captured["payload"] = kwargs["payload"]
        return {
            "visibleRuntime": "langgraph_agent_v3",
            "question": {
                "stage": "technical_follow_up",
                "stability": "stable",
                "focus": "LangGraph workflow",
                "prompt": "Explain how LangGraph orchestrates the interview agent.",
                "content": "Explain how LangGraph orchestrates the interview agent.",
            },
            "decision": {"nextAction": "deepen", "difficulty": "medium", "reason": "mainline"},
            "checkpointSummary": {"exists": True, "threadId": "fake-thread"},
            "runtimeTrace": [{"node": "observe_state"}],
            "qualityGate": {"passed": True, "reasons": []},
            "runtimeAudit": {
                "requestedRuntime": "langgraph_agent_v3",
                "allowedRuntime": "langgraph_agent_v3",
                "visibleRuntime": "langgraph_agent_v3",
                "fallbackUsed": False,
                "fallbackReason": "",
                "qualityGateReasons": [],
            },
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    monkeypatch.setattr(interview, "run_agent_runtime", fake_run_agent_runtime)

    client = TestClient(app)
    suffix = uuid4().hex
    email = f"mainline-default-{suffix}@example.com"
    username = f"mainline_default_{suffix[:8]}"
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    login = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    token = login.json()["accessToken"]

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "applicationProfileId": None,
            "profile": {"targetRole": "AI application developer", "resume": "Built a RAG interview agent"},
            "history": [{"question": "What is an Agent?", "answer": "It observes state and decides next action."}],
            "nextStage": "technical_follow_up",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert captured["agent_runtime"] == "langgraph_agent_v3"
    # v3 分派必需的键必须由路由层真实传入（含检索隔离作用域）
    assert captured["payload"]["profile"] == {
        "targetRole": "AI application developer",
        "resume": "Built a RAG interview agent",
    }
    assert captured["payload"]["history"] == [
        {"question": "What is an Agent?", "answer": "It observes state and decides next action."}
    ]
    assert captured["payload"]["next_stage"] == "technical_follow_up"
    assert captured["payload"]["agent_mode"] == "coach"
    assert captured["payload"]["application_profile_id"] is None
    assert isinstance(captured["payload"]["user_id"], int)
    assert body["prompt"] == "Explain how LangGraph orchestrates the interview agent."
    assert body["runtimeAudit"]["visibleRuntime"] == "langgraph_agent_v3"
    assert body["workflowTrace"] == [{"node": "observe_state"}]


def test_next_question_explicit_langgraph_mainline_rollback(monkeypatch) -> None:
    from backend_python.routes import interview

    captured = {}

    async def fake_call_model(messages: list[dict], temperature: float, model_name: str = "") -> dict:
        if temperature < 0.3:
            return {
                "nextAction": "deepen",
                "stage": "technical_follow_up",
                "difficulty": "medium",
                "focus": "LangGraph workflow",
                "reason": "classic decision setup",
                "tools": ["retrieve_context", "generate_question"],
                "shouldUpdateMemory": True,
                "agentMode": "coach",
            }
        return {
            "stage": "technical_follow_up",
            "stability": "dynamic",
            "focus": "LangGraph workflow",
            "prompt": "classic setup question",
        }

    async def fake_run_agent_runtime(**kwargs):
        captured["agent_runtime"] = kwargs["agent_runtime"]
        return {
            "visibleRuntime": "langgraph_mainline",
            "question": {
                "stage": "technical_follow_up",
                "stability": "stable",
                "focus": "LangGraph workflow",
                "prompt": "mainline rollback question",
                "content": "mainline rollback question",
            },
            "decision": {"nextAction": "deepen", "difficulty": "medium", "reason": "mainline"},
            "checkpointSummary": {"exists": True, "threadId": "fake-thread"},
            "runtimeTrace": [],
            "qualityGate": {"passed": True, "reasons": []},
            "runtimeAudit": {
                "requestedRuntime": "langgraph_mainline",
                "allowedRuntime": "langgraph_mainline",
                "visibleRuntime": "langgraph_mainline",
                "fallbackUsed": False,
                "fallbackReason": "",
                "qualityGateReasons": [],
            },
        }

    monkeypatch.setattr(interview, "call_model", fake_call_model)
    monkeypatch.setattr(interview, "run_agent_runtime", fake_run_agent_runtime)

    client = TestClient(app)
    suffix = uuid4().hex
    email = f"mainline-rollback-{suffix}@example.com"
    username = f"mainline_rollback_{suffix[:8]}"
    client.post("/api/auth/register", json={"email": email, "username": username, "password": "password123"})
    login = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    token = login.json()["accessToken"]

    response = client.post(
        "/api/interview/next-question",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "agentRuntime": "langgraph_mainline",
            "applicationProfileId": None,
            "profile": {"targetRole": "AI application developer", "resume": "Built a RAG interview agent"},
            "history": [],
            "nextStage": "technical_follow_up",
            "agentMode": "coach",
        },
    )

    assert response.status_code == 200
    assert captured["agent_runtime"] == "langgraph_mainline"
    assert response.json()["prompt"] == "mainline rollback question"
