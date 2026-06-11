import json

from backend_python.langgraph_agent.state import (
    assert_graph_state_jsonable,
    build_initial_graph_state,
)


def test_build_initial_graph_state_is_json_serializable():
    state = build_initial_graph_state(
        profile={"candidateName": "David", "targetRole": "AI 应用开发实习生"},
        history=[{"question": "什么是 RAG？", "answer": "不知道"}],
        next_stage="技术追问",
        agent_mode="coach",
    )

    assert state["profile"]["candidateName"] == "David"
    assert state["history"][0]["answer"] == "不知道"
    assert state["nextStage"] == "技术追问"
    assert state["agentMode"] == "coach"
    assert state["nodeTrace"] == []
    assert state["toolCalls"] == []
    json.dumps(state, ensure_ascii=False)


def test_assert_graph_state_jsonable_rejects_runtime_objects():
    class RuntimeObject:
        pass

    bad_state = {"profile": {"runtime": RuntimeObject()}}

    try:
        assert_graph_state_jsonable(bad_state)
    except TypeError as exc:
        assert "Graph state must be JSON serializable" in str(exc)
    else:
        raise AssertionError("expected non-jsonable graph state to be rejected")
