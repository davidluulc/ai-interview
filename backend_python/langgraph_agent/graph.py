from typing import Any

from langgraph.graph import END, START, StateGraph

from .checkpoint import build_graph_config, memory_saver, record_checkpoint_summary
from .nodes import (
    analyze_answer_node,
    apply_policy_node,
    generate_question_node,
    make_retrieve_context_v2_node,
    make_select_action_v2_node,
    observe_state_node,
    retrieve_context_node,
    select_action_node,
    update_memory_node,
)
from .state import InterviewGraphState, assert_graph_state_jsonable, build_initial_graph_state


def build_interview_graph():
    graph = StateGraph(InterviewGraphState)
    graph.add_node("observe_state", observe_state_node)
    graph.add_node("analyze_answer", analyze_answer_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("apply_policy", apply_policy_node)
    graph.add_node("select_action", select_action_node)
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("update_memory", update_memory_node)

    graph.add_edge(START, "observe_state")
    graph.add_edge("observe_state", "analyze_answer")
    graph.add_edge("analyze_answer", "retrieve_context")
    graph.add_edge("retrieve_context", "apply_policy")
    graph.add_edge("apply_policy", "select_action")
    graph.add_edge("select_action", "generate_question")
    graph.add_edge("generate_question", "update_memory")
    graph.add_edge("update_memory", END)
    return graph.compile()


def build_interview_graph_v2(*, retrieve_context_fn, decide_action_fn):
    graph = StateGraph(InterviewGraphState)
    graph.add_node("observe_state", observe_state_node)
    graph.add_node("analyze_answer", analyze_answer_node)
    graph.add_node("retrieve_context", make_retrieve_context_v2_node(retrieve_context_fn))
    graph.add_node("apply_policy", apply_policy_node)
    graph.add_node("select_action", make_select_action_v2_node(decide_action_fn))
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("update_memory", update_memory_node)

    graph.add_edge(START, "observe_state")
    graph.add_edge("observe_state", "analyze_answer")
    graph.add_edge("analyze_answer", "retrieve_context")
    graph.add_edge("retrieve_context", "apply_policy")
    graph.add_edge("apply_policy", "select_action")
    graph.add_edge("select_action", "generate_question")
    graph.add_edge("generate_question", "update_memory")
    graph.add_edge("update_memory", END)
    return graph.compile(checkpointer=memory_saver)


def run_interview_graph_poc(
    *,
    profile: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    next_stage: str = "",
    agent_mode: str = "interview",
) -> dict[str, Any]:
    state = build_initial_graph_state(
        profile=profile,
        history=history,
        next_stage=next_stage,
        agent_mode=agent_mode,
    )
    graph = build_interview_graph()
    result = dict(graph.invoke(state))
    assert_graph_state_jsonable(result)
    return result


async def run_interview_graph_v2(
    *,
    thread_id: str,
    profile: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    next_stage: str = "",
    agent_mode: str = "interview",
    application_profile_id: int | None = None,
    use_real_rag: bool = False,
    use_real_decision: bool = False,
    retrieve_context_fn,
    decide_action_fn,
) -> dict[str, Any]:
    state = build_initial_graph_state(
        thread_id=thread_id,
        application_profile_id=application_profile_id,
        profile=profile,
        history=history,
        next_stage=next_stage,
        agent_mode=agent_mode,
        use_real_rag=use_real_rag,
        use_real_decision=use_real_decision,
    )
    graph = build_interview_graph_v2(
        retrieve_context_fn=retrieve_context_fn,
        decide_action_fn=decide_action_fn,
    )
    result = dict(await graph.ainvoke(state, config=build_graph_config(thread_id)))
    checkpoint_summary = record_checkpoint_summary(thread_id=thread_id, state=result)
    result["checkpointSummary"] = checkpoint_summary
    result["threadId"] = str(thread_id or "default-thread")
    assert_graph_state_jsonable(result)
    return result
