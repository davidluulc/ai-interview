from backend_python.runtime_compare import compare_runtime_outputs


def test_compare_runtime_outputs_detects_matching_action_and_difficulty() -> None:
    classic = {
        "runtime": "classic",
        "question": {"content": "请解释 Agent State。"},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {},
    }
    langgraph = {
        "runtime": "langgraph",
        "nextQuestion": {"content": "请解释 Agent State。"},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {"exists": True, "threadId": "runtime-a"},
    }
    gate = {"passed": True, "fallbackToClassic": False, "reasons": [], "checks": {"checkpointAvailable": True}}

    summary = compare_runtime_outputs(classic, langgraph, gate, thread_id="runtime-a", runtime_mode="shadow")

    assert summary["threadId"] == "runtime-a"
    assert summary["runtimeMode"] == "shadow"
    assert summary["visibleRuntime"] == "classic"
    assert summary["comparison"]["actionMatched"] is True
    assert summary["comparison"]["difficultyMatched"] is True
    assert summary["comparison"]["qualityGatePassed"] is True
    assert summary["langgraph"]["checkpointExists"] is True


def test_compare_runtime_outputs_records_difference_reasons() -> None:
    classic = {
        "question": {"content": "请继续解释 RAG 日志 JSON。"},
        "decision": {"nextAction": "deep_follow_up", "difficulty": "hard"},
    }
    langgraph = {
        "nextQuestion": {"content": "我们先换一个基础问题，什么是 RAG？"},
        "decision": {"nextAction": "lower_difficulty", "difficulty": "basic"},
        "checkpointSummary": {"exists": True},
    }
    gate = {"passed": False, "fallbackToClassic": True, "reasons": ["LangGraph 标记需要人工复核"], "checks": {}}

    summary = compare_runtime_outputs(classic, langgraph, gate, thread_id="runtime-b", runtime_mode="shadow")

    assert summary["comparison"]["actionMatched"] is False
    assert summary["comparison"]["difficultyMatched"] is False
    assert summary["comparison"]["fallbackToClassic"] is True
    assert "两条链路的下一步动作不同" in summary["comparison"]["reasons"]
    assert "两条链路的难度选择不同" in summary["comparison"]["reasons"]
    assert "LangGraph 标记需要人工复核" in summary["comparison"]["reasons"]
