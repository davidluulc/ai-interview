import time
from collections.abc import Callable
from typing import Any

from .agent_trace import build_tool_call_summary


def summarize_hits(hits: list[dict[str, Any]]) -> dict[str, Any]:
    top_scores: list[float] = []
    for hit in hits:
        score = hit.get("score")
        if score is None:
            continue
        try:
            top_scores.append(round(float(score), 4))
        except (TypeError, ValueError):
            continue
        if len(top_scores) >= 3:
            break
    return {"hitCount": len(hits), "topScores": top_scores}


def run_agent_tool(
    *,
    tool_name: str,
    input_summary: dict[str, Any],
    fn: Callable[[], Any],
) -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        result = fn()
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        hits = result if isinstance(result, list) else []
        return {
            "result": result,
            "toolCall": build_tool_call_summary(
                tool_name=tool_name,
                input_summary=input_summary,
                output_summary=summarize_hits(hits),
                success=True,
                elapsed_ms=elapsed_ms,
            ),
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            "result": [],
            "toolCall": build_tool_call_summary(
                tool_name=tool_name,
                input_summary=input_summary,
                output_summary={"hitCount": 0, "topScores": []},
                success=False,
                error=str(exc),
                elapsed_ms=elapsed_ms,
            ),
        }


def retrieve_role_knowledge_tool(
    *,
    profile: dict[str, Any],
    next_stage: str,
    retrieve_fn: Callable[..., list[dict[str, Any]]],
    limit: int = 3,
    **kwargs: Any,
) -> dict[str, Any]:
    query = " ".join(
        [
            str(profile.get("targetRole") or ""),
            str(profile.get("resume") or ""),
            str(profile.get("jd") or ""),
            str(profile.get("company") or ""),
            str(next_stage or ""),
        ]
    ).strip()
    return run_agent_tool(
        tool_name="retrieve_role_knowledge",
        input_summary={"query": query, "limit": limit},
        fn=lambda: retrieve_fn(profile, next_stage, limit=limit, **kwargs),
    )


def retrieve_question_bank_tool(
    *,
    profile: dict[str, Any],
    next_stage: str,
    retrieve_fn: Callable[..., list[dict[str, Any]]],
    limit: int = 3,
    **kwargs: Any,
) -> dict[str, Any]:
    query = " ".join(
        [
            str(profile.get("targetRole") or ""),
            str(profile.get("positionTag") or ""),
            str(profile.get("resume") or ""),
            str(profile.get("jd") or ""),
            str(profile.get("company") or ""),
            str(next_stage or ""),
        ]
    ).strip()
    return run_agent_tool(
        tool_name="retrieve_question_bank",
        input_summary={"query": query, "limit": limit},
        fn=lambda: retrieve_fn(profile, next_stage, limit=limit, **kwargs),
    )


def retrieve_candidate_memory_tool(
    *,
    profile: dict[str, Any],
    retrieve_fn: Callable[..., list[dict[str, Any]]],
    limit: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    query = " ".join(
        [
            str(profile.get("targetRole") or ""),
            str(profile.get("resume") or ""),
            str(profile.get("jd") or ""),
        ]
    ).strip()
    return run_agent_tool(
        tool_name="retrieve_candidate_memory",
        input_summary={"query": query, "limit": limit},
        fn=lambda: retrieve_fn(profile, limit=limit, **kwargs),
    )

