from collections.abc import Awaitable, Callable
from typing import Any

from .agent_tools import (
    retrieve_candidate_memory_tool,
    retrieve_question_bank_tool,
    retrieve_role_knowledge_tool,
)
from .agent_trace import build_node_trace
from .interview_agent import build_agent_state, build_decision_summary, decide_next_action
from .agent_policy import apply_agent_policy
from .weakness_training_templates import select_training_template_hint


async def run_next_question_agent(
    *,
    profile: dict[str, Any],
    history: list[dict[str, Any]],
    next_stage: str,
    agent_mode: str,
    role_retrieve_fn: Callable[..., list[dict[str, Any]]],
    question_retrieve_fn: Callable[..., list[dict[str, Any]]],
    memory_retrieve_fn: Callable[..., list[dict[str, Any]]],
    call_model_fn: Callable[..., Awaitable[dict[str, Any]]] | Callable[..., dict[str, Any]],
    decide_next_action_fn: Callable[..., Awaitable[dict[str, Any]]] = decide_next_action,
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

    agent_state = build_agent_state(
        profile=profile,
        history=history,
        next_stage=next_stage,
        role_hits=role_hits,
        question_hits=question_hits,
        memory_hits=memory_hits,
        agent_mode=agent_mode,
    )
    answer_analysis = agent_state.get("answerAnalysis") if isinstance(agent_state.get("answerAnalysis"), dict) else {}
    weakness_strategy = agent_state.get("weaknessStrategy") if isinstance(agent_state.get("weaknessStrategy"), dict) else {}
    policy = apply_agent_policy(agent_state)
    agent_state["policy"] = policy
    node_trace = [
        build_node_trace(
            node_name="observe_state",
            input_summary={"historyCount": len(history or []), "agentMode": agent_mode},
            output_summary={
                "roundCount": agent_state.get("roundCount"),
                "remainingRounds": agent_state.get("remainingRounds"),
                "answerStatus": agent_state.get("answerStatus"),
            },
        ),
        build_node_trace(
            node_name="analyze_answer",
            input_summary={
                "historyCount": len(history or []),
                "lastAnswerLength": len(str((history or [{}])[-1].get("answer") or "")) if history else 0,
            },
            output_summary={
                "answerStatus": agent_state.get("answerStatus"),
                "weakAnswerStreak": answer_analysis.get("weakAnswerStreak", 0),
                "repeatedQuestionCount": answer_analysis.get("repeatedQuestionCount", 0),
                "triggerSignals": answer_analysis.get("triggerSignals", []),
                "topicLocked": bool((answer_analysis.get("topicLock") or {}).get("locked")),
            },
        ),
        build_node_trace(
            node_name="retrieve_context",
            input_summary={"nextStage": next_stage},
            output_summary={
                "roleHitCount": len(role_hits),
                "questionHitCount": len(question_hits),
                "memoryHitCount": len(memory_hits),
            },
            fallback_used=any(not call.get("success") for call in tool_calls),
        ),
        build_node_trace(
            node_name="select_weakness_strategy",
            input_summary={
                "frequentWeakTags": (agent_state.get("candidateProfile") or {}).get("frequentWeakTags", []),
                "agentMode": agent_mode,
            },
            output_summary={
                "enabled": bool(weakness_strategy.get("enabled")),
                "primaryWeakTag": weakness_strategy.get("primaryWeakTag", ""),
                "modePolicy": weakness_strategy.get("modePolicy", "none"),
                "recommendedAction": weakness_strategy.get("recommendedAction", ""),
            },
            fallback_used=bool(weakness_strategy.get("guardrailApplied")),
        ),
        build_node_trace(
            node_name="apply_policy",
            input_summary={
                "agentMode": agent_mode,
                "weakAnswerStreak": answer_analysis.get("weakAnswerStreak", 0),
                "repeatedQuestionCount": answer_analysis.get("repeatedQuestionCount", 0),
            },
            output_summary={
                "recommendedAction": policy.get("recommendedAction", ""),
                "difficulty": policy.get("difficulty", ""),
                "shouldExplainBeforeAsk": bool(policy.get("shouldExplainBeforeAsk")),
                "shouldAskUserChoice": bool(policy.get("shouldAskUserChoice")),
                "requiresHumanReview": bool(policy.get("requiresHumanReview")),
            },
            fallback_used=False,
        ),
    ]
    agent_state["toolCalls"] = tool_calls
    agent_state["nodeTrace"] = node_trace

    agent_decision = await decide_next_action_fn(agent_state, call_model_fn=call_model_fn)
    agent_decision.setdefault("policy", policy)
    training_template_hint = (
        agent_decision.get("trainingTemplateHint")
        if isinstance(agent_decision.get("trainingTemplateHint"), dict)
        else select_training_template_hint(
            weakness_strategy=weakness_strategy,
            agent_mode=agent_mode,
            difficulty=str(agent_decision.get("difficulty") or "medium"),
        )
    )
    agent_decision["trainingTemplateHint"] = training_template_hint
    agent_decision.setdefault("triggerRules", [])
    agent_decision.setdefault("guardrailApplied", False)
    agent_decision.setdefault("decisionSummary", build_decision_summary(agent_decision))
    node_trace = [
        *node_trace,
        build_node_trace(
            node_name="select_training_template",
            input_summary={
                "primaryWeakTag": weakness_strategy.get("primaryWeakTag", ""),
                "agentMode": agent_mode,
                "difficulty": agent_decision.get("difficulty"),
            },
            output_summary={
                "enabled": bool(training_template_hint.get("enabled")),
                "weakTag": training_template_hint.get("weakTag", ""),
                "label": training_template_hint.get("label", ""),
                "recommendedQuestion": training_template_hint.get("recommendedQuestion", ""),
            },
            fallback_used=bool(training_template_hint.get("fallbackUsed")),
        ),
        build_node_trace(
            node_name="select_action",
            input_summary={
                "answerStatus": agent_state.get("answerStatus"),
                "remainingRounds": agent_state.get("remainingRounds"),
            },
            output_summary={
                "nextAction": agent_decision.get("nextAction"),
                "difficulty": agent_decision.get("difficulty"),
                "focus": agent_decision.get("focus"),
            },
            fallback_used=bool(agent_decision.get("fallbackUsed")),
        ),
    ]
    agent_state["nodeTrace"] = node_trace
    agent_decision["toolCalls"] = tool_calls
    agent_decision["nodeTrace"] = node_trace

    return {
        "roleHits": role_hits,
        "questionHits": question_hits,
        "memoryHits": memory_hits,
        "toolCalls": tool_calls,
        "nodeTrace": node_trace,
        "agentState": agent_state,
        "agentDecision": agent_decision,
    }
