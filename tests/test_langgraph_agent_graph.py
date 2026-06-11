from backend_python.langgraph_agent.graph import build_interview_graph, run_interview_graph_poc


def test_build_interview_graph_compiles():
    graph = build_interview_graph()

    assert graph is not None


def test_run_interview_graph_poc_returns_trace_and_question():
    result = run_interview_graph_poc(
        profile={"candidateName": "David", "targetRole": "AI 应用开发实习生"},
        history=[{"question": "讲讲 RAG。", "answer": "不知道"}],
        next_stage="技术追问",
        agent_mode="coach",
    )

    assert result["decision"]["nextAction"] == "lower_difficulty"
    assert result["nextQuestion"]["prompt"]
    assert result["memoryUpdate"]["status"] == "deferred"
    assert [item["nodeName"] for item in result["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "apply_policy",
        "select_action",
        "generate_question",
        "update_memory",
    ]
