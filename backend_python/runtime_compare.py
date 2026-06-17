from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .runtime_quality_gate import extract_runtime_decision, extract_runtime_question


def _difficulty(result: dict[str, Any]) -> str:
    return str(extract_runtime_decision(result).get("difficulty") or "")


def _next_action(result: dict[str, Any]) -> str:
    return str(extract_runtime_decision(result).get("nextAction") or "")


def _question_similarity(left: str, right: str) -> float:
    left_normalized = " ".join(str(left or "").split())
    right_normalized = " ".join(str(right or "").split())
    if not left_normalized or not right_normalized:
        return 0.0
    return round(SequenceMatcher(None, left_normalized, right_normalized).ratio(), 2)


def compare_runtime_outputs(
    classic_result: dict[str, Any],
    langgraph_result: dict[str, Any],
    quality_gate: dict[str, Any],
    *,
    thread_id: str,
    runtime_mode: str,
) -> dict[str, Any]:
    classic_question = extract_runtime_question(classic_result)
    langgraph_question = extract_runtime_question(langgraph_result)
    classic_action = _next_action(classic_result)
    langgraph_action = _next_action(langgraph_result)
    classic_difficulty = _difficulty(classic_result)
    langgraph_difficulty = _difficulty(langgraph_result)
    checkpoint = langgraph_result.get("checkpointSummary") if isinstance(langgraph_result.get("checkpointSummary"), dict) else {}

    action_matched = classic_action == langgraph_action
    difficulty_matched = classic_difficulty == langgraph_difficulty
    reasons: list[str] = []
    if not action_matched:
        reasons.append("两条链路的下一步动作不同")
    if not difficulty_matched:
        reasons.append("两条链路的难度选择不同")
    reasons.extend(str(reason) for reason in quality_gate.get("reasons", []) if str(reason).strip())
    if not reasons:
        reasons.append("LangGraph 与 classic 本轮关键决策一致")

    return {
        "threadId": str(thread_id or ""),
        "runtimeMode": str(runtime_mode or ""),
        "visibleRuntime": "classic" if runtime_mode == "shadow" else str(runtime_mode or ""),
        "classic": {
            "status": str(classic_result.get("status") or "completed"),
            "nextAction": classic_action,
            "difficulty": classic_difficulty,
            "questionText": classic_question,
        },
        "langgraph": {
            "status": str(langgraph_result.get("status") or "completed"),
            "nextAction": langgraph_action,
            "difficulty": langgraph_difficulty,
            "questionText": langgraph_question,
            "checkpointExists": bool(checkpoint.get("exists") or checkpoint.get("threadId")),
            "requiresHumanReview": bool(
                langgraph_result.get("requiresHumanReview")
                or extract_runtime_decision(langgraph_result).get("requiresHumanReview")
                or checkpoint.get("requiresHumanReview")
            ),
        },
        "comparison": {
            "actionMatched": action_matched,
            "difficultyMatched": difficulty_matched,
            "questionSimilarity": _question_similarity(classic_question, langgraph_question),
            "qualityGatePassed": bool(quality_gate.get("passed")),
            "fallbackToClassic": bool(quality_gate.get("fallbackToClassic")),
            "reasons": reasons,
        },
    }
