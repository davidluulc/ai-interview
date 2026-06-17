from __future__ import annotations

from typing import Any


VALID_REQUESTED_RUNTIMES = {"classic", "shadow", "langgraph_canary"}


def decide_runtime_policy(
    *,
    requested_runtime: str | None,
    user_role: str | None,
    agent_mode: str | None,
) -> dict[str, Any]:
    requested = (requested_runtime or "classic").strip() or "classic"
    role = (user_role or "user").strip().lower()
    mode = (agent_mode or "coach").strip().lower()

    if requested not in VALID_REQUESTED_RUNTIMES:
        return {
            "requestedRuntime": requested,
            "allowedRuntime": "classic",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": False,
            "requiresAudit": True,
            "agentMode": mode,
            "reasons": ["请求的 runtime 不合法，已降级为 classic"],
        }

    if requested == "classic":
        return {
            "requestedRuntime": "classic",
            "allowedRuntime": "classic",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": False,
            "requiresAudit": False,
            "agentMode": mode,
            "reasons": ["未请求实验链路，默认使用稳定 classic Agent"],
        }

    if role != "admin":
        return {
            "requestedRuntime": requested,
            "allowedRuntime": "classic",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": False,
            "requiresAudit": True,
            "agentMode": mode,
            "reasons": ["普通用户暂不开放 LangGraph 灰度链路"],
        }

    if requested == "shadow":
        return {
            "requestedRuntime": "shadow",
            "allowedRuntime": "shadow",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": True,
            "requiresAudit": True,
            "agentMode": mode,
            "reasons": ["管理员账号允许使用 shadow 对比链路"],
        }

    return {
        "requestedRuntime": "langgraph_canary",
        "allowedRuntime": "langgraph",
        "fallbackRuntime": "classic",
        "visibleRuntimeOnSuccess": "langgraph",
        "visibleRuntimeOnFailure": "classic",
        "canUseLangGraph": True,
        "requiresAudit": True,
        "agentMode": mode,
        "reasons": ["管理员账号允许使用 LangGraph 灰度链路"],
    }
