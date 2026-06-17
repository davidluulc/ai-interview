import json
from typing import Any

from .db_models import AgentDecisionLog, RagRetrievalLog
from .rag_logging import serialize_rag_log


def safe_json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def serialize_datetime(value: Any) -> str | None:
    return value.isoformat() if value else None


def normalize_rag_name(value: str) -> str:
    labels = {
        "role_knowledge": "岗位知识库",
        "question_bank": "题库",
        "candidate_memory": "候选人画像",
        "memory": "候选人画像",
    }
    return labels.get(value or "", value or "未知知识库")


def action_label(value: str) -> str:
    labels = {
        "deepen": "继续深挖",
        "deep_follow_up": "继续深挖",
        "lower_difficulty": "降低难度",
        "raise_difficulty": "提高难度",
        "shift_topic": "切换话题",
        "switch_topic": "切换话题",
        "finish_interview": "结束面试",
        "end_interview": "结束面试",
        "summarize_feedback": "总结反馈",
        "practice_weakness": "专项训练",
    }
    return labels.get(value or "", value or "未知动作")


def quality_level_from_hit_count(hit_count: int) -> str:
    if hit_count <= 0:
        return "miss"
    if hit_count == 1:
        return "weak"
    return "good"


def extract_thread_id(state: dict[str, Any], decision: dict[str, Any], fallback: str) -> str:
    candidates = [
        state.get("threadId"),
        state.get("thread_id"),
        decision.get("threadId"),
        decision.get("thread_id"),
    ]
    for candidate in candidates:
        if str(candidate or "").strip():
            return str(candidate).strip()
    return fallback


def _diagnostic(type_: str, level: str, title: str, message: str) -> dict[str, str]:
    return {"type": type_, "level": level, "title": title, "message": message}


def build_ai_debug_diagnostics(
    *,
    agent: dict[str, Any],
    rag_items: list[dict[str, Any]],
    langgraph: dict[str, Any],
) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    if agent.get("fallbackUsed"):
        diagnostics.append(
            _diagnostic(
                "fallback_used",
                "warning",
                "兜底规则已启用",
                "模型决策输出不稳定，系统已使用 fallback 规则保证流程继续。",
            )
        )

    for item in rag_items:
        retriever = str(item.get("retrieverLabel") or item.get("retrieverName") or "知识库")
        hit_count = int(item.get("hitCount") or 0)
        quality_level = str(item.get("qualityLevel") or quality_level_from_hit_count(hit_count))
        if hit_count == 0 or quality_level == "miss":
            diagnostics.append(
                _diagnostic(
                    "empty_recall",
                    "warning",
                    f"{retriever}空召回",
                    f"{retriever}没有召回可用资料，建议补充知识库内容或检查 query rewrite、metadata filter。",
                )
            )
        elif quality_level == "weak":
            diagnostics.append(
                _diagnostic(
                    "weak_recall",
                    "info",
                    f"{retriever}弱召回",
                    f"{retriever}召回质量偏弱，建议补充题库样例、优化 chunk 标题或调整检索关键词。",
                )
            )

    policy = agent.get("policy") if isinstance(agent.get("policy"), dict) else {}
    if policy.get("requiresHumanReview"):
        diagnostics.append(
            _diagnostic(
                "human_review",
                "warning",
                "建议人工复核",
                "Agent Policy 标记本轮决策需要人工复核，适合检查是否出现连续追问或难度异常。",
            )
        )

    if not langgraph.get("exists"):
        diagnostics.append(
            _diagnostic(
                "missing_checkpoint",
                "info",
                "未找到 LangGraph checkpoint",
                "本次请求可能未启用 LangGraph 旁路，当前主流程仍由 classic Agent 执行。",
            )
        )
    quality_gate = langgraph.get("qualityGate") if isinstance(langgraph.get("qualityGate"), dict) else {}
    if quality_gate and not quality_gate.get("passed", True):
        diagnostics.append(
            _diagnostic(
                "runtime_quality_gate_failed",
                "warning",
                "LangGraph 输出未通过门禁",
                "本轮 LangGraph 结果没有进入可见链路，系统应回退 classic Agent。",
            )
        )
    return diagnostics


def serialize_rag_trace_item(log: RagRetrievalLog) -> dict[str, Any]:
    item = serialize_rag_log(log)
    hit_count = int(item.get("hitCount") or 0)
    quality = item.get("quality") if isinstance(item.get("quality"), dict) else {}
    quality_level = str(quality.get("level") or quality_level_from_hit_count(hit_count))
    hits = item.get("hits") if isinstance(item.get("hits"), list) else []
    return {
        "id": item.get("id"),
        "queryText": item.get("queryText") or "",
        "retrieverName": item.get("retrieverName") or "",
        "retrieverLabel": normalize_rag_name(str(item.get("retrieverName") or "")),
        "retrievalMode": item.get("retrievalMode") or "",
        "hitCount": hit_count,
        "qualityLevel": quality_level,
        "usedInPrompt": bool(item.get("usedInPrompt", True)),
        "topHits": hits[:3],
        "createdAt": item.get("createdAt"),
    }


def serialize_agent_trace(log: AgentDecisionLog) -> dict[str, Any]:
    state = safe_json_loads(log.state_json, {})
    decision = safe_json_loads(log.decision_json, {})
    tools = safe_json_loads(log.tools_json, [])
    policy = decision.get("policy") if isinstance(decision.get("policy"), dict) else {}
    if not policy:
        policy = {
            "policyReasons": decision.get("policyReasons") or [],
            "triggerRules": decision.get("triggerRules") or [],
            "requiresHumanReview": bool(decision.get("requiresHumanReview")),
        }
    return {
        "nextAction": log.next_action,
        "nextActionLabel": action_label(log.next_action),
        "stage": log.stage,
        "difficulty": log.difficulty,
        "focus": log.focus,
        "reason": log.reason,
        "tools": tools if isinstance(tools, list) else [],
        "state": state if isinstance(state, dict) else {},
        "decision": decision if isinstance(decision, dict) else {},
        "policy": policy,
        "fallbackUsed": bool(log.fallback_used),
    }


def normalize_checkpoint(checkpoint: dict[str, Any], thread_id: str) -> dict[str, Any]:
    exists = bool(checkpoint.get("exists"))
    return {
        "enabled": bool(checkpoint.get("enabled", True)),
        "exists": exists,
        "threadId": checkpoint.get("threadId") or thread_id,
        "runtime": checkpoint.get("runtime") or "",
        "status": checkpoint.get("status") or ("available" if exists else "missing"),
        "currentNode": checkpoint.get("currentNode") or "",
        "roundCount": int(checkpoint.get("roundCount") or 0),
        "lastAction": checkpoint.get("lastAction") or "",
        "lastQuestion": checkpoint.get("lastQuestion") or "",
        "nodeTraceCount": int(checkpoint.get("nodeTraceCount") or 0),
        "stateKeys": checkpoint.get("stateKeys") if isinstance(checkpoint.get("stateKeys"), list) else [],
        "policyRecommendedAction": checkpoint.get("policyRecommendedAction") or "",
        "requiresHumanReview": bool(checkpoint.get("requiresHumanReview")),
        "policyReasons": checkpoint.get("policyReasons") if isinstance(checkpoint.get("policyReasons"), list) else [],
        "policyTriggerRules": checkpoint.get("policyTriggerRules")
        if isinstance(checkpoint.get("policyTriggerRules"), list)
        else [],
        "interrupt": checkpoint.get("interrupt") if isinstance(checkpoint.get("interrupt"), dict) else None,
        "resumeDecision": checkpoint.get("resumeDecision") or "",
        "runtimeTrace": checkpoint.get("runtimeTrace") if isinstance(checkpoint.get("runtimeTrace"), list) else [],
        "qualityGate": checkpoint.get("qualityGate") if isinstance(checkpoint.get("qualityGate"), dict) else {},
        "comparisonSummary": checkpoint.get("comparisonSummary")
        if isinstance(checkpoint.get("comparisonSummary"), dict)
        else {},
        "runtimeAudit": checkpoint.get("runtimeAudit") if isinstance(checkpoint.get("runtimeAudit"), dict) else {},
        "visibleRuntime": (
            checkpoint.get("comparisonSummary", {}).get("visibleRuntime")
            if isinstance(checkpoint.get("comparisonSummary"), dict)
            else ""
        )
        or checkpoint.get("visibleRuntime")
        or checkpoint.get("runtime")
        or "",
        "explanation": "LangGraph checkpoint 已记录本轮旁路状态。"
        if exists
        else "本次请求未启用 LangGraph 旁路。当前主流程仍由 classic Agent 执行。",
    }


def build_ai_debug_recent_item(
    log: AgentDecisionLog,
    rag_logs: list[RagRetrievalLog],
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    agent = serialize_agent_trace(log)
    state = agent["state"] if isinstance(agent.get("state"), dict) else {}
    decision = agent["decision"] if isinstance(agent.get("decision"), dict) else {}
    thread_id = extract_thread_id(state, decision, f"agent-log-{log.id}")
    langgraph = normalize_checkpoint(checkpoint, thread_id)
    rag_items = [serialize_rag_trace_item(rag_log) for rag_log in rag_logs]
    diagnostics = build_ai_debug_diagnostics(agent=agent, rag_items=rag_items, langgraph=langgraph)
    return {
        "traceId": log.id,
        "createdAt": serialize_datetime(log.created_at),
        "userId": log.user_id,
        "applicationProfileId": log.application_profile_id,
        "requestType": log.request_type,
        "agentMode": str(state.get("agentMode") or state.get("agent_mode") or ""),
        "nextAction": log.next_action,
        "nextActionLabel": action_label(log.next_action),
        "difficulty": log.difficulty,
        "fallbackUsed": bool(log.fallback_used),
        "totalRagHits": sum(int(item.get("hitCount") or 0) for item in rag_items),
        "threadId": thread_id,
        "diagnostics": diagnostics,
    }


def build_ai_debug_detail(
    log: AgentDecisionLog,
    rag_logs: list[RagRetrievalLog],
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    agent = serialize_agent_trace(log)
    state = agent["state"] if isinstance(agent.get("state"), dict) else {}
    decision = agent["decision"] if isinstance(agent.get("decision"), dict) else {}
    thread_id = extract_thread_id(state, decision, f"agent-log-{log.id}")
    langgraph = normalize_checkpoint(checkpoint, thread_id)
    rag_items = [serialize_rag_trace_item(rag_log) for rag_log in rag_logs]
    diagnostics = build_ai_debug_diagnostics(agent=agent, rag_items=rag_items, langgraph=langgraph)
    return {
        "summary": {
            "traceId": log.id,
            "createdAt": serialize_datetime(log.created_at),
            "userId": log.user_id,
            "applicationProfileId": log.application_profile_id,
            "requestType": log.request_type,
            "agentMode": str(state.get("agentMode") or state.get("agent_mode") or ""),
            "stage": log.stage,
            "roundCount": int(state.get("roundCount") or 0) if isinstance(state, dict) else 0,
            "remainingRounds": int(state.get("remainingRounds") or 0) if isinstance(state, dict) else 0,
            "threadId": thread_id,
        },
        "rag": {
            "items": rag_items,
            "totalHitCount": sum(int(item.get("hitCount") or 0) for item in rag_items),
            "relation": "按 userId、applicationProfileId 和最近时间尽力关联",
        },
        "agent": agent,
        "langgraph": langgraph,
        "diagnostics": diagnostics,
    }
