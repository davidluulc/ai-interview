from __future__ import annotations

from typing import Any

from .contracts import get_node_contracts, validate_node_trace


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _add_unique(items: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _get_node_trace(summary: dict[str, Any]) -> list[dict[str, Any]]:
    node_trace = _as_list(summary.get("nodeTrace"))
    if node_trace:
        return [item for item in node_trace if isinstance(item, dict)]

    raw_summary = _as_dict(summary.get("rawSummary"))
    raw_trace = _as_list(raw_summary.get("nodeTrace"))
    return [item for item in raw_trace if isinstance(item, dict)]


def _build_timeline(summary: dict[str, Any], node_trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contracts = {item["name"]: item for item in get_node_contracts()}
    timeline: list[dict[str, Any]] = []

    for index, item in enumerate(node_trace, start=1):
        node = str(item.get("node") or "").strip()
        contract = contracts.get(node, {})
        title = str(contract.get("title") or node or "未知节点")
        detail = _node_detail(node=node, summary=summary, raw_item=item)
        timeline.append(
            {
                "step": index,
                "node": node or "unknown",
                "title": title,
                "detail": detail,
            }
        )

    if not timeline and summary.get("currentNode"):
        node = str(summary.get("currentNode") or "")
        contract = contracts.get(node, {})
        timeline.append(
            {
                "step": 1,
                "node": node,
                "title": str(contract.get("title") or node),
                "detail": _node_detail(node=node, summary=summary, raw_item={}),
            }
        )

    return timeline


def _node_detail(*, node: str, summary: dict[str, Any], raw_item: dict[str, Any]) -> str:
    if node == "observe_state":
        return "读取历史问答、候选人档案、RAG 命中摘要和当前模式。"
    if node == "retrieve_context":
        return "调用岗位知识库、题库和候选人画像检索上下文。"
    if node == "analyze_answer":
        return "分析上一轮回答质量，识别是否存在连续弱回答。"
    if node == "apply_policy":
        return "根据回答质量、模式和风险规则生成策略建议。"
    if node == "decide_action":
        return "根据当前 Agent State 生成下一步动作和难度。"
    if node == "human_review":
        reason = _as_dict(summary.get("interrupt")).get("reason") or raw_item.get("reason") or "触发人工复核。"
        return str(reason)
    if node == "generate_question":
        return "根据决策、检索上下文和历史问答生成下一题。"
    if node == "update_memory":
        return "把本轮回答分析和训练线索写入候选人记忆摘要。"
    return "该节点不在当前契约列表中，需要检查 nodeTrace 来源。"


def _collect_risks(summary: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    runtime_audit = _as_dict(summary.get("runtimeAudit"))
    quality_gate = _as_dict(summary.get("qualityGate"))

    if summary.get("requiresHumanReview"):
        _add_unique(risks, "requires_human_review")
    if runtime_audit.get("fallbackUsed"):
        _add_unique(risks, "fallback_used")

    for reason in _as_list(runtime_audit.get("qualityGateReasons")):
        _add_unique(risks, reason)
    for reason in _as_list(quality_gate.get("reasons")):
        _add_unique(risks, reason)

    return risks


def _next_actions(summary: dict[str, Any], risks: list[str]) -> list[str]:
    status = str(summary.get("status") or "")
    if status == "interrupted":
        return ["resume", "fallback_classic"]
    if "fallback_used" in risks:
        return ["inspect_quality_gate", "fallback_classic"]
    if not summary.get("exists"):
        return []
    return ["inspect_timeline"]


def _summary_text(summary: dict[str, Any], risks: list[str]) -> str:
    if not summary.get("exists"):
        return "未找到 LangGraph 运行记录。"

    status = str(summary.get("status") or "completed")
    current_node = str(summary.get("currentNode") or "")
    if status == "interrupted":
        reason = str(_as_dict(summary.get("interrupt")).get("reason") or "需要人工复核。")
        node_label = current_node or "human_review"
        return f"本轮 LangGraph 在 {node_label} 节点暂停：{reason}"

    if "fallback_used" in risks:
        return "本轮 LangGraph 已回退到 classic Agent，可查看质量门禁原因。"

    if status == "failed":
        return "本轮 LangGraph 执行失败，需要查看 runtimeTrace 和质量门禁原因。"

    return "本轮 LangGraph 执行完成，可查看节点时间线和运行摘要。"


def build_runtime_replay(summary: dict[str, Any]) -> dict[str, Any]:
    safe_summary = summary if isinstance(summary, dict) else {}
    node_trace = _get_node_trace(safe_summary)
    node_validation = validate_node_trace(node_trace)
    risks = _collect_risks(safe_summary)

    return {
        "threadId": str(safe_summary.get("threadId") or ""),
        "exists": bool(safe_summary.get("exists")),
        "status": str(safe_summary.get("status") or "missing"),
        "summary": _summary_text(safe_summary, risks),
        "timeline": _build_timeline(safe_summary, node_trace) if safe_summary.get("exists") else [],
        "risks": risks,
        "nextActions": _next_actions(safe_summary, risks),
        "nodeValidation": node_validation,
    }
