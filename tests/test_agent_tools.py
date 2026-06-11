from backend_python.agent_tools import (
    retrieve_candidate_memory_tool,
    retrieve_question_bank_tool,
    retrieve_role_knowledge_tool,
    run_agent_tool,
    summarize_hits,
)


def test_run_agent_tool_records_success_result_and_elapsed_time():
    wrapped = run_agent_tool(
        tool_name="retrieve_question_bank",
        input_summary={"query": "RAG", "limit": 2},
        fn=lambda: [{"title": "RAG 基础", "score": 0.91}, {"title": "Agent", "score": 0.82}],
    )

    assert wrapped["result"][0]["title"] == "RAG 基础"
    assert wrapped["toolCall"]["toolName"] == "retrieve_question_bank"
    assert wrapped["toolCall"]["success"] is True
    assert wrapped["toolCall"]["outputSummary"]["hitCount"] == 2
    assert wrapped["toolCall"]["outputSummary"]["topScores"] == [0.91, 0.82]
    assert wrapped["toolCall"]["elapsedMs"] >= 0


def test_run_agent_tool_records_empty_hits_as_success():
    wrapped = run_agent_tool(
        tool_name="retrieve_role_knowledge",
        input_summary={"query": "不存在的知识点"},
        fn=lambda: [],
    )

    assert wrapped["result"] == []
    assert wrapped["toolCall"]["success"] is True
    assert wrapped["toolCall"]["outputSummary"]["hitCount"] == 0
    assert wrapped["toolCall"]["error"] == ""


def test_run_agent_tool_records_exception_without_crashing():
    def broken_tool():
        raise TimeoutError("retrieval timeout")

    wrapped = run_agent_tool(
        tool_name="retrieve_candidate_memory",
        input_summary={"query": "候选人画像"},
        fn=broken_tool,
    )

    assert wrapped["result"] == []
    assert wrapped["toolCall"]["success"] is False
    assert "retrieval timeout" in wrapped["toolCall"]["error"]


def test_retrieval_tool_wrappers_call_current_retrievers():
    profile = {"targetRole": "AI 应用开发实习生", "resume": "RAG Agent"}

    role = retrieve_role_knowledge_tool(
        profile=profile,
        next_stage="技术追问",
        retrieve_fn=lambda profile, next_stage, limit: [{"score": 0.7, "title": next_stage}],
        limit=1,
    )
    question = retrieve_question_bank_tool(
        profile=profile,
        next_stage="技术追问",
        retrieve_fn=lambda profile, next_stage, limit: [{"score": 0.8, "question": next_stage}],
        limit=1,
    )
    memory = retrieve_candidate_memory_tool(
        profile=profile,
        retrieve_fn=lambda profile, limit: [{"score": 0.6, "content": profile["resume"]}],
        limit=1,
    )

    assert role["toolCall"]["toolName"] == "retrieve_role_knowledge"
    assert question["toolCall"]["toolName"] == "retrieve_question_bank"
    assert memory["toolCall"]["toolName"] == "retrieve_candidate_memory"
    assert role["toolCall"]["outputSummary"]["hitCount"] == 1


def test_summarize_hits_handles_missing_scores():
    summary = summarize_hits([{"title": "A"}, {"score": "0.42"}, {"score": None}])

    assert summary == {"hitCount": 3, "topScores": [0.42]}

