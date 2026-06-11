from backend_python.langgraph_agent.nodes import (
    analyze_answer_node,
    apply_policy_node,
    generate_question_node,
    observe_state_node,
    retrieve_context_node,
    select_action_node,
    update_memory_node,
)
from backend_python.langgraph_agent.state import build_initial_graph_state


def test_observe_and_analyze_answer_nodes_append_trace():
    state = build_initial_graph_state(
        profile={"candidateName": "David"},
        history=[{"question": "什么是 RAG？", "answer": "不知道"}],
        next_stage="技术追问",
        agent_mode="coach",
    )

    observed = observe_state_node(state)
    analyzed = analyze_answer_node({**state, **observed})

    assert observed["nodeTrace"][0]["nodeName"] == "observe_state"
    assert analyzed["answerAnalysis"]["weakAnswerStreak"] == 1
    assert analyzed["answerAnalysis"]["answerStatus"] == "不会"
    assert analyzed["nodeTrace"][-1]["nodeName"] == "analyze_answer"


def test_retrieve_context_node_returns_three_tool_calls():
    state = build_initial_graph_state(profile={"targetRole": "AI 应用开发"}, history=[])

    update = retrieve_context_node(state)

    assert len(update["roleHits"]) == 1
    assert len(update["questionHits"]) == 1
    assert len(update["memoryHits"]) == 1
    assert [call["toolName"] for call in update["toolCalls"]] == [
        "retrieve_role_knowledge",
        "retrieve_question_bank",
        "retrieve_candidate_memory",
    ]
    assert update["nodeTrace"][-1]["nodeName"] == "retrieve_context"


def test_apply_policy_node_returns_policy_and_trace():
    state = build_initial_graph_state(
        profile={"targetRole": "AI 应用开发"},
        history=[
            {"question": "RAG 日志怎么写？", "answer": "不知道"},
            {"question": "那 query_text 是什么？", "answer": "不会"},
        ],
        agent_mode="coach",
    )
    state = {**state, **observe_state_node(state)}
    state = {**state, **analyze_answer_node(state)}
    state = {**state, **retrieve_context_node(state)}

    update = apply_policy_node(state)

    assert update["policy"]["recommendedAction"] == "lower_difficulty"
    assert update["policy"]["shouldExplainBeforeAsk"] is True
    assert update["policy"]["shouldAskUserChoice"] is True
    assert update["policySummary"]["recommendedAction"] == "lower_difficulty"
    assert update["nodeTrace"][-1]["nodeName"] == "apply_policy"


def test_decision_question_and_memory_nodes_build_outputs():
    state = build_initial_graph_state(
        profile={"targetRole": "AI 应用开发实习生"},
        history=[{"question": "讲讲 RAG。", "answer": "不知道"}],
        agent_mode="coach",
    )
    for node in (
        observe_state_node,
        analyze_answer_node,
        retrieve_context_node,
        apply_policy_node,
        select_action_node,
        generate_question_node,
        update_memory_node,
    ):
        state = {**state, **node(state)}

    assert state["decision"]["nextAction"] == "lower_difficulty"
    assert state["decision"]["fallbackUsed"] is False
    assert "RAG" in state["nextQuestion"]["prompt"]
    assert state["memoryUpdate"]["status"] == "deferred"
    assert [item["nodeName"] for item in state["nodeTrace"]] == [
        "observe_state",
        "analyze_answer",
        "retrieve_context",
        "apply_policy",
        "select_action",
        "generate_question",
        "update_memory",
    ]
