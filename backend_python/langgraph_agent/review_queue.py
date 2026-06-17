from __future__ import annotations

from typing import Any


SUPPORTED_REVIEW_DECISIONS = {
    "continue_interview",
    "switch_to_coach",
    "fallback_classic",
    "end_interview",
}

DEFAULT_REVIEW_OPTIONS = ["continue_interview", "switch_to_coach", "fallback_classic", "end_interview"]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_review_decision(decision: str) -> str:
    normalized = str(decision or "").strip()
    if normalized not in SUPPORTED_REVIEW_DECISIONS:
        raise ValueError(f"Unsupported human review decision: {normalized}")
    return normalized


def _needs_review(item: dict[str, Any]) -> bool:
    return str(item.get("status") or "") == "interrupted" or bool(item.get("requiresHumanReview"))


def _review_reason(item: dict[str, Any]) -> str:
    interrupt = _as_dict(item.get("interrupt"))
    reason = str(interrupt.get("reason") or "").strip()
    if reason:
        return reason
    if item.get("requiresHumanReview"):
        return "Agent policy 标记需要人工复核。"
    return "LangGraph runtime 已暂停，等待人工恢复决策。"


def _review_options(item: dict[str, Any]) -> list[str]:
    interrupt = _as_dict(item.get("interrupt"))
    options = [str(option).strip() for option in _as_list(interrupt.get("options")) if str(option or "").strip()]
    valid_options = [option for option in options if option in SUPPORTED_REVIEW_DECISIONS]
    return valid_options or list(DEFAULT_REVIEW_OPTIONS)


def build_review_queue(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict) or not _needs_review(item):
            continue

        queue.append(
            {
                "threadId": str(item.get("threadId") or ""),
                "status": str(item.get("status") or ""),
                "currentNode": str(item.get("currentNode") or ""),
                "reason": _review_reason(item),
                "options": _review_options(item),
                "lastQuestion": str(item.get("lastQuestion") or ""),
                "createdAt": item.get("createdAt"),
            }
        )

    return queue
