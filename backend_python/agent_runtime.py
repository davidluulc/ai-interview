from __future__ import annotations

from typing import Any, Awaitable, Callable

from .runtime_audit import build_runtime_audit
from .runtime_compare import compare_runtime_outputs
from .runtime_quality_gate import evaluate_runtime_quality


RuntimeRunner = Callable[..., Awaitable[dict[str, Any]]]


def normalize_agent_runtime(value: str | None) -> str:
    runtime = str(value or "langgraph_mainline").strip().lower()
    allowed = {"classic", "langgraph", "shadow", "langgraph_canary", "langgraph_mainline"}
    return runtime if runtime in allowed else "langgraph_mainline"


def _extract_question(result: dict[str, Any]) -> dict[str, Any]:
    question = result.get("question")
    if isinstance(question, dict):
        return question
    next_question = result.get("nextQuestion")
    if isinstance(next_question, dict):
        return next_question
    return {}


def _extract_recent_questions(payload: dict[str, Any]) -> list[str]:
    recent = payload.get("recentQuestions") or payload.get("recent_questions") or []
    if not isinstance(recent, list):
        return []
    return [str(item) for item in recent if str(item or "").strip()]


def _runtime_response(*, runtime: str, thread_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime": runtime,
        "visibleRuntime": runtime,
        "threadId": thread_id,
        "status": str(result.get("status") or "completed"),
        "question": _extract_question(result),
        "decision": result.get("decision") if isinstance(result.get("decision"), dict) else {},
        "checkpointSummary": result.get("checkpointSummary") if isinstance(result.get("checkpointSummary"), dict) else {},
        "interrupt": result.get("interrupt") if isinstance(result.get("interrupt"), dict) else None,
        "runtimeTrace": result.get("runtimeTrace") if isinstance(result.get("runtimeTrace"), list) else [],
        "qualityGate": result.get("qualityGate") if isinstance(result.get("qualityGate"), dict) else None,
        "comparisonSummary": result.get("comparisonSummary") if isinstance(result.get("comparisonSummary"), dict) else None,
        "fallbackRuntime": "",
        "shadow": None,
    }


def _failed_langgraph_result(thread_id: str, error: Exception | str) -> dict[str, Any]:
    return {
        "status": "failed",
        "nextQuestion": {},
        "decision": {},
        "checkpointSummary": {"exists": False, "threadId": thread_id},
        "runtimeTrace": [],
        "error": str(error),
    }


def _failed_quality_gate(reason: str) -> dict[str, Any]:
    return {
        "passed": False,
        "fallbackToClassic": True,
        "riskLevel": "high",
        "reasons": [reason],
        "checks": {
            "runtimeCompleted": False,
            "nonEmptyQuestion": False,
            "validDecision": False,
            "validDifficulty": False,
            "checkpointAvailable": False,
        },
    }


async def run_agent_runtime(
    *,
    agent_runtime: str | None,
    thread_id: str,
    classic_runner: RuntimeRunner,
    langgraph_runner: RuntimeRunner,
    payload: dict[str, Any],
) -> dict[str, Any]:
    runtime = normalize_agent_runtime(agent_runtime)
    common = {"thread_id": thread_id, **payload}
    recent_questions = _extract_recent_questions(payload)

    if runtime == "classic":
        classic_result = await classic_runner(**common)
        response = _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)
        response["runtimeAudit"] = build_runtime_audit(
            policy={
                "requestedRuntime": "classic",
                "allowedRuntime": "classic",
                "fallbackRuntime": "classic",
                "reasons": ["未请求实验链路，默认使用稳定 classic Agent"],
            },
            quality_gate=None,
            checkpoint_summary=response["checkpointSummary"],
            comparison_summary=None,
            visible_runtime="classic",
        )
        return response

    if runtime == "langgraph_mainline":
        try:
            langgraph_result = await langgraph_runner(**common)
            quality_gate = evaluate_runtime_quality(langgraph_result, recent_questions=recent_questions)
        except Exception as exc:
            langgraph_result = _failed_langgraph_result(thread_id, exc)
            quality_gate = _failed_quality_gate("LangGraph runtime 执行失败")

        policy = {
            "requestedRuntime": "langgraph_mainline",
            "allowedRuntime": "langgraph_mainline",
            "fallbackRuntime": "classic",
            "reasons": ["默认使用 LangGraph mainline"],
        }

        if quality_gate["passed"]:
            response = _runtime_response(runtime="langgraph_mainline", thread_id=thread_id, result=langgraph_result)
            response["visibleRuntime"] = "langgraph_mainline"
            response["qualityGate"] = quality_gate
            response["comparisonSummary"] = None
            response["runtimeAudit"] = build_runtime_audit(
                policy=policy,
                quality_gate=quality_gate,
                checkpoint_summary=response["checkpointSummary"],
                comparison_summary=None,
                visible_runtime="langgraph_mainline",
            )
            return response

        classic_result = await classic_runner(**common)
        response = _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)
        response["visibleRuntime"] = "classic"
        response["fallbackRuntime"] = "classic"
        response["qualityGate"] = quality_gate
        response["comparisonSummary"] = None
        response["runtimeTrace"] = (
            langgraph_result.get("runtimeTrace") if isinstance(langgraph_result.get("runtimeTrace"), list) else []
        )
        response["runtimeAudit"] = build_runtime_audit(
            policy=policy,
            quality_gate=quality_gate,
            checkpoint_summary=langgraph_result.get("checkpointSummary")
            if isinstance(langgraph_result.get("checkpointSummary"), dict)
            else {},
            comparison_summary=None,
            visible_runtime="classic",
        )
        return response

    if runtime == "langgraph_canary":
        classic_result = await classic_runner(**common)
        try:
            langgraph_result = await langgraph_runner(**common)
            quality_gate = evaluate_runtime_quality(langgraph_result, recent_questions=recent_questions)
        except Exception as exc:
            langgraph_result = {
                "status": "failed",
                "nextQuestion": {},
                "decision": {},
                "checkpointSummary": {"exists": False, "threadId": thread_id},
                "error": str(exc),
            }
            quality_gate = {
                "passed": False,
                "fallbackToClassic": True,
                "riskLevel": "high",
                "reasons": ["LangGraph runtime 执行失败"],
                "checks": {
                    "runtimeCompleted": False,
                    "nonEmptyQuestion": False,
                    "validDecision": False,
                    "validDifficulty": False,
                    "checkpointAvailable": False,
                },
            }
        comparison = compare_runtime_outputs(
            classic_result,
            langgraph_result,
            quality_gate,
            thread_id=thread_id,
            runtime_mode="langgraph_canary",
        )
        policy = {
            "requestedRuntime": "langgraph_canary",
            "allowedRuntime": "langgraph",
            "fallbackRuntime": "classic",
            "reasons": ["LangGraph 灰度链路已进入 runtime 执行层"],
        }

        if quality_gate["passed"]:
            response = _runtime_response(runtime="langgraph", thread_id=thread_id, result=langgraph_result)
            visible_runtime = "langgraph"
        else:
            response = _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)
            response["fallbackRuntime"] = "classic"
            visible_runtime = "classic"

        response["visibleRuntime"] = visible_runtime
        response["qualityGate"] = quality_gate
        response["comparisonSummary"] = comparison
        response["runtimeAudit"] = build_runtime_audit(
            policy=policy,
            quality_gate=quality_gate,
            checkpoint_summary=langgraph_result.get("checkpointSummary")
            if isinstance(langgraph_result.get("checkpointSummary"), dict)
            else {},
            comparison_summary=comparison,
            visible_runtime=visible_runtime,
        )
        response["shadow"] = {
            "runtime": "langgraph",
            "status": str(langgraph_result.get("status") or "completed"),
            "question": _extract_question(langgraph_result),
            "decision": langgraph_result.get("decision") if isinstance(langgraph_result.get("decision"), dict) else {},
            "checkpointSummary": langgraph_result.get("checkpointSummary")
            if isinstance(langgraph_result.get("checkpointSummary"), dict)
            else {},
            "qualityGate": quality_gate,
            "comparisonSummary": comparison,
            "runtimeTrace": langgraph_result.get("runtimeTrace") if isinstance(langgraph_result.get("runtimeTrace"), list) else [],
        }
        return response

    if runtime == "langgraph":
        try:
            langgraph_result = await langgraph_runner(**common)
            quality_gate = evaluate_runtime_quality(langgraph_result, recent_questions=recent_questions)
        except Exception as exc:
            langgraph_result = {
                "status": "failed",
                "nextQuestion": {},
                "decision": {},
                "checkpointSummary": {"exists": False, "threadId": thread_id},
                "error": str(exc),
            }
            quality_gate = {
                "passed": False,
                "fallbackToClassic": True,
                "riskLevel": "high",
                "reasons": ["LangGraph runtime 执行失败"],
                "checks": {
                    "runtimeCompleted": False,
                    "nonEmptyQuestion": False,
                    "validDecision": False,
                    "validDifficulty": False,
                    "checkpointAvailable": False,
                },
            }
        if quality_gate["passed"]:
            response = _runtime_response(runtime="langgraph", thread_id=thread_id, result=langgraph_result)
            response["qualityGate"] = quality_gate
            response["comparisonSummary"] = compare_runtime_outputs(
                langgraph_result,
                langgraph_result,
                quality_gate,
                thread_id=thread_id,
                runtime_mode="langgraph",
            )
            response["runtimeAudit"] = build_runtime_audit(
                policy={
                    "requestedRuntime": "langgraph",
                    "allowedRuntime": "langgraph",
                    "fallbackRuntime": "classic",
                    "reasons": ["请求使用 LangGraph runtime"],
                },
                quality_gate=quality_gate,
                checkpoint_summary=response["checkpointSummary"],
                comparison_summary=response["comparisonSummary"],
                visible_runtime="langgraph",
            )
            return response

        classic_result = await classic_runner(**common)
        response = _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)
        response["fallbackRuntime"] = "langgraph"
        response["qualityGate"] = quality_gate
        response["comparisonSummary"] = compare_runtime_outputs(
            classic_result,
            langgraph_result,
            quality_gate,
            thread_id=thread_id,
            runtime_mode="langgraph",
        )
        response["runtimeAudit"] = build_runtime_audit(
            policy={
                "requestedRuntime": "langgraph",
                "allowedRuntime": "langgraph",
                "fallbackRuntime": "classic",
                "reasons": ["请求使用 LangGraph runtime"],
            },
            quality_gate=quality_gate,
            checkpoint_summary=langgraph_result.get("checkpointSummary")
            if isinstance(langgraph_result.get("checkpointSummary"), dict)
            else {},
            comparison_summary=response["comparisonSummary"],
            visible_runtime="classic",
        )
        return response

    classic_result = await classic_runner(**common)
    response = _runtime_response(runtime="classic", thread_id=thread_id, result=classic_result)
    if runtime == "shadow":
        try:
            shadow_result = await langgraph_runner(**common)
            quality_gate = evaluate_runtime_quality(shadow_result, recent_questions=recent_questions)
        except Exception as exc:
            shadow_result = {
                "status": "failed",
                "nextQuestion": {},
                "decision": {},
                "checkpointSummary": {"exists": False, "threadId": thread_id},
                "error": str(exc),
            }
            quality_gate = {
                "passed": False,
                "fallbackToClassic": True,
                "riskLevel": "high",
                "reasons": ["LangGraph runtime 执行失败"],
                "checks": {
                    "runtimeCompleted": False,
                    "nonEmptyQuestion": False,
                    "validDecision": False,
                    "validDifficulty": False,
                    "checkpointAvailable": False,
                },
            }
        comparison = compare_runtime_outputs(
            classic_result,
            shadow_result,
            quality_gate,
            thread_id=thread_id,
            runtime_mode="shadow",
        )
        response["visibleRuntime"] = "classic"
        response["qualityGate"] = quality_gate
        response["comparisonSummary"] = comparison
        response["runtimeAudit"] = build_runtime_audit(
            policy={
                "requestedRuntime": "shadow",
                "allowedRuntime": "shadow",
                "fallbackRuntime": "classic",
                "reasons": ["shadow 模式只做后台对比，可见链路保持 classic"],
            },
            quality_gate=quality_gate,
            checkpoint_summary=shadow_result.get("checkpointSummary")
            if isinstance(shadow_result.get("checkpointSummary"), dict)
            else {},
            comparison_summary=comparison,
            visible_runtime="classic",
        )
        response["shadow"] = {
            "runtime": "langgraph",
            "status": str(shadow_result.get("status") or "completed"),
            "question": _extract_question(shadow_result),
            "decision": shadow_result.get("decision") if isinstance(shadow_result.get("decision"), dict) else {},
            "checkpointSummary": shadow_result.get("checkpointSummary")
            if isinstance(shadow_result.get("checkpointSummary"), dict)
            else {},
            "qualityGate": quality_gate,
            "comparisonSummary": comparison,
            "runtimeTrace": shadow_result.get("runtimeTrace") if isinstance(shadow_result.get("runtimeTrace"), list) else [],
        }

    return response
