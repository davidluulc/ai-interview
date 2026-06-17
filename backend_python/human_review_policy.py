from __future__ import annotations

from typing import Any


DEFAULT_REVIEW_OPTIONS = ["continue_interview", "switch_to_coach", "end_interview"]


def evaluate_human_review(
    *,
    agent_policy: dict[str, Any] | None,
    answer_analysis: dict[str, Any] | None,
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    policy = agent_policy if isinstance(agent_policy, dict) else {}
    analysis = answer_analysis if isinstance(answer_analysis, dict) else {}
    trigger_rules: list[str] = []

    if bool(policy.get("requiresHumanReview")):
        trigger_rules.append("policy_requires_human_review")

    weak_streak = int(analysis.get("weakAnswerStreak") or 0)
    if weak_streak >= 3:
        trigger_rules.append("weak_answer_streak")

    recent_history = list(history or [])[-3:]
    repeated_empty = len(recent_history) >= 2 and all(not str(item.get("answer") or "").strip() for item in recent_history)
    if repeated_empty:
        trigger_rules.append("repeated_empty_answer")

    if not trigger_rules:
        return {
            "shouldInterrupt": False,
            "reason": "",
            "options": [],
            "triggerRules": [],
        }

    reason = "Agent 工作流触发人工复核："
    if "weak_answer_streak" in trigger_rules:
        reason += "候选人连续弱回答，建议选择继续面试、切到学习辅导或结束面试。"
    elif "policy_requires_human_review" in trigger_rules:
        reason += "Agent Policy 标记本轮决策需要人工确认。"
    else:
        reason += "候选人连续空回答，建议人工确认下一步。"

    return {
        "shouldInterrupt": True,
        "reason": reason,
        "options": list(DEFAULT_REVIEW_OPTIONS),
        "triggerRules": trigger_rules,
    }
