from __future__ import annotations

from typing import Any


VALID_REQUESTED_RUNTIMES = {"classic", "shadow", "langgraph_canary", "langgraph_mainline"}


def _mainline_policy(*, requested: str, mode: str) -> dict[str, Any]:
    return {
        "requestedRuntime": requested,
        "allowedRuntime": "langgraph_mainline",
        "fallbackRuntime": "classic",
        "visibleRuntimeOnSuccess": "langgraph_mainline",
        "visibleRuntimeOnFailure": "classic",
        "canUseLangGraph": True,
        "requiresAudit": True,
        "agentMode": mode,
        "reasons": ["默认使用 LangGraph mainline，classic Agent 仅作为 fallback"],
    }


def decide_runtime_policy(
    *,
    requested_runtime: str | None,
    user_role: str | None,
    agent_mode: str | None,
) -> dict[str, Any]:
    requested = (requested_runtime or "langgraph_mainline").strip() or "langgraph_mainline"
    role = (user_role or "user").strip().lower()
    mode = (agent_mode or "coach").strip().lower()

    if requested not in VALID_REQUESTED_RUNTIMES:
        return _mainline_policy(requested="langgraph_mainline", mode=mode)

    if requested == "langgraph_mainline":
        return _mainline_policy(requested="langgraph_mainline", mode=mode)

    if requested == "classic":
        return {
            "requestedRuntime": "classic",
            "allowedRuntime": "classic",
            "fallbackRuntime": "classic",
            "visibleRuntimeOnSuccess": "classic",
            "visibleRuntimeOnFailure": "classic",
            "canUseLangGraph": False,
            "requiresAudit": True,
            "agentMode": mode,
            "reasons": ["显式请求 classic fallback/debug runtime"],
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
