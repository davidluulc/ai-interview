from collections.abc import Awaitable, Callable
from typing import Any

from backend_python.agent_tools import (
    retrieve_candidate_memory_tool,
    retrieve_question_bank_tool,
    retrieve_role_knowledge_tool,
)
from backend_python.interview_agent import build_agent_state, decide_next_action
from backend_python.rag_quality import evaluate_retrieval_quality


def retrieve_real_context_for_graph(
    *,
    profile: dict[str, Any],
    next_stage: str,
    role_retrieve_fn: Callable[..., list[dict[str, Any]]],
    question_retrieve_fn: Callable[..., list[dict[str, Any]]],
    memory_retrieve_fn: Callable[..., list[dict[str, Any]]],
    role_retrieve_kwargs: dict[str, Any] | None = None,
    question_retrieve_kwargs: dict[str, Any] | None = None,
    memory_retrieve_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role_tool = retrieve_role_knowledge_tool(
        profile=profile,
        next_stage=next_stage,
        retrieve_fn=role_retrieve_fn,
        **dict(role_retrieve_kwargs or {}),
    )
    question_tool = retrieve_question_bank_tool(
        profile=profile,
        next_stage=next_stage,
        retrieve_fn=question_retrieve_fn,
        **dict(question_retrieve_kwargs or {}),
    )
    memory_tool = retrieve_candidate_memory_tool(
        profile=profile,
        retrieve_fn=memory_retrieve_fn,
        **dict(memory_retrieve_kwargs or {}),
    )
    role_hits = role_tool["result"]
    question_hits = question_tool["result"]
    memory_hits = memory_tool["result"]
    tool_calls = [role_tool["toolCall"], question_tool["toolCall"], memory_tool["toolCall"]]
    return {
        "roleHits": role_hits,
        "questionHits": question_hits,
        "memoryHits": memory_hits,
        "toolCalls": tool_calls,
        "retrievalQuality": {
            "roleKnowledge": evaluate_retrieval_quality(role_hits),
            "questionBank": evaluate_retrieval_quality(question_hits),
            "candidateMemory": evaluate_retrieval_quality(memory_hits),
        },
    }


async def decide_real_action_for_graph(
    *,
    profile: dict[str, Any],
    history: list[dict[str, Any]],
    next_stage: str,
    agent_mode: str,
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
    call_model_fn: Callable[..., Awaitable[dict[str, Any]]] | Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    agent_state = build_agent_state(
        profile=profile,
        history=history,
        next_stage=next_stage,
        role_hits=role_hits,
        question_hits=question_hits,
        memory_hits=memory_hits,
        agent_mode=agent_mode,
    )
    decision = await decide_next_action(agent_state, call_model_fn=call_model_fn)
    return {"agentState": agent_state, "decision": decision}
