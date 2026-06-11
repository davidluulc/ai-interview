from typing import Any


def summarize_text(value: Any, *, limit: int = 120) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def build_node_trace(
    *,
    node_name: str,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    fallback_used: bool = False,
    elapsed_ms: int = 0,
    error: str = "",
) -> dict[str, Any]:
    return {
        "nodeName": str(node_name),
        "inputSummary": dict(input_summary or {}),
        "outputSummary": dict(output_summary or {}),
        "fallbackUsed": bool(fallback_used),
        "elapsedMs": max(int(elapsed_ms or 0), 0),
        "error": str(error or ""),
    }


def build_tool_call_summary(
    *,
    tool_name: str,
    input_summary: dict[str, Any] | None = None,
    output_summary: dict[str, Any] | None = None,
    success: bool = True,
    error: str = "",
    elapsed_ms: int = 0,
) -> dict[str, Any]:
    return {
        "toolName": str(tool_name),
        "inputSummary": dict(input_summary or {}),
        "outputSummary": dict(output_summary or {}),
        "success": bool(success),
        "error": str(error or ""),
        "elapsedMs": max(int(elapsed_ms or 0), 0),
    }

