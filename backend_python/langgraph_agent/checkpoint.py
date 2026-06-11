from typing import Any

from langgraph.checkpoint.memory import MemorySaver


memory_saver = MemorySaver()
_checkpoint_summaries: dict[str, dict[str, Any]] = {}


def normalize_thread_id(thread_id: str) -> str:
    return str(thread_id or "default-thread").strip() or "default-thread"


def build_graph_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": normalize_thread_id(thread_id)}}


def record_checkpoint_summary(*, thread_id: str, state: dict[str, Any]) -> dict[str, Any]:
    safe_thread_id = normalize_thread_id(thread_id)
    node_trace = state.get("nodeTrace") if isinstance(state.get("nodeTrace"), list) else []
    decision = state.get("decision") if isinstance(state.get("decision"), dict) else {}
    policy = state.get("policy") if isinstance(state.get("policy"), dict) else {}
    next_question = state.get("nextQuestion") if isinstance(state.get("nextQuestion"), dict) else {}
    summary = {
        "enabled": True,
        "exists": True,
        "threadId": safe_thread_id,
        "roundCount": int(state.get("roundCount") or 0),
        "lastAction": str(decision.get("nextAction") or ""),
        "lastQuestion": str(next_question.get("prompt") or ""),
        "nodeTraceCount": len(node_trace),
        "stateKeys": sorted(str(key) for key in state.keys()),
        "policyRecommendedAction": str(policy.get("recommendedAction") or ""),
        "shouldAskUserChoice": bool(policy.get("shouldAskUserChoice")),
        "requiresHumanReview": bool(policy.get("requiresHumanReview")),
        "policyReasons": list(policy.get("policyReasons") or [])[:3],
        "policyTriggerRules": list(policy.get("triggerRules") or []),
    }
    _checkpoint_summaries[safe_thread_id] = summary
    return summary


def summarize_checkpoint(thread_id: str) -> dict[str, Any]:
    safe_thread_id = normalize_thread_id(thread_id)
    if safe_thread_id not in _checkpoint_summaries:
        return {
            "enabled": True,
            "exists": False,
            "threadId": safe_thread_id,
            "roundCount": 0,
            "lastAction": "",
            "lastQuestion": "",
            "nodeTraceCount": 0,
            "stateKeys": [],
            "policyRecommendedAction": "",
            "shouldAskUserChoice": False,
            "requiresHumanReview": False,
            "policyReasons": [],
            "policyTriggerRules": [],
        }
    return dict(_checkpoint_summaries[safe_thread_id])
