from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any


VALID_ACTIONS = {
    "deepen",
    "deep_follow_up",
    "lower_difficulty",
    "raise_difficulty",
    "shift_topic",
    "switch_topic",
    "finish_interview",
    "end_interview",
    "summarize_feedback",
    "practice_weakness",
}

VALID_DIFFICULTIES = {"basic", "easy", "medium", "hard", "advanced"}


def extract_runtime_question(result: dict[str, Any]) -> str:
    question = result.get("question") if isinstance(result.get("question"), dict) else {}
    next_question = result.get("nextQuestion") if isinstance(result.get("nextQuestion"), dict) else {}
    return str(
        question.get("content")
        or question.get("prompt")
        or next_question.get("content")
        or next_question.get("prompt")
        or ""
    ).strip()


def extract_runtime_decision(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("decision") if isinstance(result.get("decision"), dict) else {}


def is_repeated_question(question: str, recent_questions: list[str], *, threshold: float = 0.88) -> bool:
    normalized_question = " ".join(str(question or "").split())
    if not normalized_question:
        return False
    for recent in recent_questions[-3:]:
        normalized_recent = " ".join(str(recent or "").split())
        if not normalized_recent:
            continue
        if normalized_question == normalized_recent:
            return True
        if SequenceMatcher(None, normalized_question, normalized_recent).ratio() >= threshold:
            return True
    return False


def evaluate_runtime_quality(result: dict[str, Any], recent_questions: list[str] | None = None) -> dict[str, Any]:
    safe_result = result if isinstance(result, dict) else {}
    recent = recent_questions or []
    question = extract_runtime_question(safe_result)
    decision = extract_runtime_decision(safe_result)
    checkpoint = safe_result.get("checkpointSummary") if isinstance(safe_result.get("checkpointSummary"), dict) else {}

    next_action = str(decision.get("nextAction") or "")
    difficulty = str(decision.get("difficulty") or "")
    requires_human_review = bool(
        safe_result.get("requiresHumanReview")
        or decision.get("requiresHumanReview")
        or checkpoint.get("requiresHumanReview")
    )

    checks = {
        "nonEmptyQuestion": bool(question),
        "validDecision": next_action in VALID_ACTIONS,
        "validDifficulty": difficulty in VALID_DIFFICULTIES,
        "notRepeated": not is_repeated_question(question, recent),
        "checkpointAvailable": bool(checkpoint.get("exists") or checkpoint.get("threadId")),
        "humanReviewBlocked": requires_human_review,
    }

    reasons: list[str] = []
    if not checks["nonEmptyQuestion"]:
        reasons.append("LangGraph 没有生成可展示的问题")
    if not checks["validDecision"]:
        reasons.append(f"LangGraph 决策动作不合法：{next_action or '空'}")
    if not checks["validDifficulty"]:
        reasons.append(f"LangGraph 难度等级不合法：{difficulty or '空'}")
    if not checks["notRepeated"]:
        reasons.append("LangGraph 问题与最近问题重复度过高")
    if not checks["checkpointAvailable"]:
        reasons.append("LangGraph 缺少 checkpoint 摘要")
    if checks["humanReviewBlocked"]:
        reasons.append("LangGraph 标记需要人工复核")

    passed = (
        checks["nonEmptyQuestion"]
        and checks["validDecision"]
        and checks["validDifficulty"]
        and checks["notRepeated"]
        and checks["checkpointAvailable"]
        and not checks["humanReviewBlocked"]
    )

    return {
        "passed": passed,
        "fallbackToClassic": not passed,
        "riskLevel": "low" if passed else "high",
        "reasons": reasons,
        "checks": checks,
    }
