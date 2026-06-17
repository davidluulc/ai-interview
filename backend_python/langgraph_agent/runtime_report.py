from __future__ import annotations

from collections import Counter
from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _quality_reasons(item: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    runtime_audit = _as_dict(item.get("runtimeAudit"))
    quality_gate = _as_dict(item.get("qualityGate"))

    for reason in _as_list(runtime_audit.get("qualityGateReasons")):
        text = str(reason or "").strip()
        if text:
            reasons.append(text)
    for reason in _as_list(quality_gate.get("reasons")):
        text = str(reason or "").strip()
        if text:
            reasons.append(text)

    return reasons


def _needs_human_review(item: dict[str, Any]) -> bool:
    return bool(item.get("requiresHumanReview")) or bool(_as_dict(item.get("interrupt")))


def _summary(total: int, fallback_count: int, human_review_count: int) -> str:
    if total == 0:
        return "暂无 LangGraph runtime 运行记录。"
    if fallback_count or human_review_count:
        return f"该线程共 {total} 次运行，其中 {fallback_count} 次 fallback、{human_review_count} 次触发人工复核，需要继续观察。"
    return f"该线程共 {total} 次运行，暂未发现 fallback 或人工复核风险。"


def build_runtime_report(thread_id: str, items: list[dict[str, Any]] | None) -> dict[str, Any]:
    safe_items = [item for item in items or [] if isinstance(item, dict)]
    status_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    fallback_count = 0
    human_review_count = 0

    for item in safe_items:
        status = str(item.get("status") or "unknown")
        status_counts[status] += 1

        runtime_audit = _as_dict(item.get("runtimeAudit"))
        if runtime_audit.get("fallbackUsed"):
            fallback_count += 1
        if _needs_human_review(item):
            human_review_count += 1

        reason_counts.update(_quality_reasons(item))

    top_reasons = [
        {"reason": reason, "count": count}
        for reason, count in sorted(reason_counts.items(), key=lambda pair: (-pair[1], pair[0]))
    ]

    return {
        "threadId": str(thread_id or ""),
        "totalRuns": len(safe_items),
        "statusCounts": dict(status_counts),
        "fallbackCount": fallback_count,
        "humanReviewCount": human_review_count,
        "topQualityGateReasons": top_reasons,
        "summary": _summary(len(safe_items), fallback_count, human_review_count),
    }
