import json

from backend_python.agent_trace import build_node_trace, build_tool_call_summary, summarize_text


def test_build_node_trace_records_node_input_output_and_fallback():
    trace = build_node_trace(
        node_name="select_action",
        input_summary={"answerStatus": "不会", "remainingRounds": 5},
        output_summary={"nextAction": "lower_difficulty", "difficulty": "basic"},
        fallback_used=True,
        elapsed_ms=12,
    )

    json.dumps(trace, ensure_ascii=False)
    assert trace["nodeName"] == "select_action"
    assert trace["fallbackUsed"] is True
    assert trace["elapsedMs"] == 12
    assert trace["error"] == ""


def test_build_tool_call_summary_records_success_and_error():
    ok = build_tool_call_summary(
        tool_name="retrieve_question_bank",
        input_summary={"query": "RAG", "limit": 4},
        output_summary={"hitCount": 2, "topScores": [0.91, 0.82]},
        success=True,
        elapsed_ms=8,
    )
    failed = build_tool_call_summary(
        tool_name="retrieve_role_knowledge",
        input_summary={"query": "Agent"},
        output_summary={},
        success=False,
        error="timeout",
        elapsed_ms=1000,
    )

    assert ok["success"] is True
    assert failed["success"] is False
    assert failed["error"] == "timeout"


def test_summarize_text_limits_long_sensitive_text():
    text = "A" * 300
    summary = summarize_text(text, limit=40)

    assert len(summary) <= 41
    assert summary.endswith("…")

