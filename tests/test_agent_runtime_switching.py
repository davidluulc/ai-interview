import asyncio

from backend_python.agent_runtime import run_agent_runtime


def test_agent_runtime_defaults_to_langgraph_agent_v3(monkeypatch) -> None:
    from backend_python.langgraph_agent import graph_v3

    async def fake_run_interview_graph_v3(**kwargs):
        return {
            "question": {"content": "v3 default question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
            "nodeTrace": [{"node": "plan", "tool": "retrieve_role_knowledge"}],
        }

    monkeypatch.setattr(graph_v3, "run_interview_graph_v3", fake_run_interview_graph_v3)

    async def classic_runner(**kwargs):
        raise AssertionError("classic runner should not be called when v3 passes the quality gate")

    async def langgraph_runner(**kwargs):
        raise AssertionError("langgraph v2 runner should not be called under v3 default")

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="",
            thread_id="runtime-a",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "ok"},
        )
    )

    assert result["runtime"] == "langgraph_agent_v3"
    assert result["status"] == "completed"
    assert result["question"]["content"] == "v3 default question"
    assert result["shadow"] is None
    # v3 图输出的 nodeTrace 必须透传到 runtimeTrace（后台诊断台可观测）
    assert result["runtimeTrace"] == [{"node": "plan", "tool": "retrieve_role_knowledge"}]


def test_agent_runtime_runs_langgraph_mode() -> None:
    async def classic_runner(**kwargs):
        raise AssertionError("classic runner should not be called")

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": "langgraph question"},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph",
            thread_id="runtime-b",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会"},
        )
    )

    assert result["runtime"] == "langgraph"
    assert result["status"] == "completed"
    assert result["question"]["content"] == "langgraph question"
    assert result["decision"]["nextAction"] == "lower_difficulty"


def test_agent_runtime_shadow_returns_classic_and_records_langgraph_summary() -> None:
    async def classic_runner(**kwargs):
        return {"question": {"content": "classic visible question"}, "decision": {"nextAction": "deep_follow_up"}}

    async def langgraph_runner(**kwargs):
        return {"nextQuestion": {"content": "shadow question"}, "decision": {"nextAction": "lower_difficulty"}}

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="shadow",
            thread_id="runtime-c",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会"},
        )
    )

    assert result["runtime"] == "classic"
    assert result["status"] == "completed"
    assert result["question"]["content"] == "classic visible question"
    assert result["shadow"]["runtime"] == "langgraph"
    assert result["shadow"]["question"]["content"] == "shadow question"


def test_agent_runtime_langgraph_falls_back_to_classic_when_gate_fails() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic fallback question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": ""},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph",
            thread_id="runtime-gate-fail",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": ["什么是 RAG？"]},
        )
    )

    assert result["runtime"] == "classic"
    assert result["visibleRuntime"] == "classic"
    assert result["fallbackRuntime"] == "langgraph"
    assert result["question"]["content"] == "classic fallback question"
    assert result["qualityGate"]["passed"] is False
    assert result["comparisonSummary"]["comparison"]["fallbackToClassic"] is True


def test_agent_runtime_shadow_records_quality_gate_and_comparison_summary() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic visible question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": "langgraph shadow question"},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="shadow",
            thread_id="runtime-shadow-v4",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": []},
        )
    )

    assert result["runtime"] == "classic"
    assert result["visibleRuntime"] == "classic"
    assert result["shadow"]["runtime"] == "langgraph"
    assert result["shadow"]["qualityGate"]["passed"] is True
    assert result["shadow"]["comparisonSummary"]["threadId"] == "runtime-shadow-v4"
    assert result["comparisonSummary"]["comparison"]["actionMatched"] is False


def test_langgraph_canary_uses_langgraph_when_quality_gate_passes() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic fallback question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": "langgraph visible question"},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_canary",
            thread_id="runtime-canary-pass",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": ["什么是 FastAPI？"]},
        )
    )

    assert result["runtime"] == "langgraph"
    assert result["visibleRuntime"] == "langgraph"
    assert result["question"]["content"] == "langgraph visible question"
    assert result["qualityGate"]["passed"] is True
    assert result["runtimeAudit"]["requestedRuntime"] == "langgraph_canary"
    assert result["runtimeAudit"]["visibleRuntime"] == "langgraph"
    assert result["runtimeAudit"]["fallbackUsed"] is False


def test_langgraph_canary_falls_back_to_classic_when_quality_gate_fails() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic fallback question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        return {
            "nextQuestion": {"content": ""},
            "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
            "checkpointSummary": {"exists": True, "threadId": kwargs["thread_id"]},
        }

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_canary",
            thread_id="runtime-canary-fail",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "不会", "recentQuestions": ["什么是 RAG？"]},
        )
    )

    assert result["runtime"] == "classic"
    assert result["visibleRuntime"] == "classic"
    assert result["question"]["content"] == "classic fallback question"
    assert result["qualityGate"]["passed"] is False
    assert result["runtimeAudit"]["requestedRuntime"] == "langgraph_canary"
    assert result["runtimeAudit"]["visibleRuntime"] == "classic"
    assert result["runtimeAudit"]["fallbackUsed"] is True


def test_langgraph_canary_falls_back_to_classic_when_langgraph_runner_errors() -> None:
    async def classic_runner(**kwargs):
        return {
            "question": {"content": "classic fallback question"},
            "decision": {"nextAction": "deep_follow_up", "difficulty": "medium"},
        }

    async def langgraph_runner(**kwargs):
        raise RuntimeError("LLM provider request failed")

    result = asyncio.run(
        run_agent_runtime(
            agent_runtime="langgraph_canary",
            thread_id="runtime-canary-error",
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={"answer": "我不确定", "recentQuestions": ["什么是 LangGraph？"]},
        )
    )

    assert result["runtime"] == "classic"
    assert result["visibleRuntime"] == "classic"
    assert result["question"]["content"] == "classic fallback question"
    assert result["qualityGate"]["passed"] is False
    assert "LangGraph runtime 执行失败" in result["qualityGate"]["reasons"]
    assert result["runtimeAudit"]["fallbackUsed"] is True
