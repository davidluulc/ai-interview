from __future__ import annotations

from typing import Any


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def build_runtime_audit(
    *,
    policy: dict[str, Any],
    quality_gate: dict[str, Any] | None,
    checkpoint_summary: dict[str, Any] | None,
    comparison_summary: dict[str, Any] | None,
    visible_runtime: str,
) -> dict[str, Any]:
    gate = quality_gate if isinstance(quality_gate, dict) else {}
    checkpoint = checkpoint_summary if isinstance(checkpoint_summary, dict) else {}
    comparison = comparison_summary if isinstance(comparison_summary, dict) else {}
    comparison_block = comparison.get("comparison") if isinstance(comparison.get("comparison"), dict) else {}

    fallback_runtime = str(policy.get("fallbackRuntime") or "classic")
    fallback_used = bool(
        gate.get("fallbackToClassic")
        or comparison_block.get("fallbackToClassic")
        or (visible_runtime == fallback_runtime and policy.get("allowedRuntime") != fallback_runtime)
    )

    return {
        "requestedRuntime": str(policy.get("requestedRuntime") or "classic"),
        "allowedRuntime": str(policy.get("allowedRuntime") or "classic"),
        "visibleRuntime": str(visible_runtime or "classic"),
        "fallbackRuntime": fallback_runtime,
        "fallbackUsed": fallback_used,
        "qualityGatePassed": bool(gate.get("passed", visible_runtime == "classic")),
        "qualityGateReasons": _string_list(gate.get("reasons")),
        "policyReasons": _string_list(policy.get("reasons")),
        "checkpointExists": bool(checkpoint.get("exists") or checkpoint.get("threadId")),
        "requiresHumanReview": bool(checkpoint.get("requiresHumanReview")),
    }
