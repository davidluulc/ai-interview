from __future__ import annotations

from typing import Any


NODE_CONTRACTS: list[dict[str, Any]] = [
    {
        "name": "observe_state",
        "title": "观察当前状态",
        "inputs": ["profile", "history", "agentMode", "runtime"],
        "outputs": ["agentState", "nodeTrace"],
        "risks": [],
    },
    {
        "name": "retrieve_context",
        "title": "检索三类 RAG 上下文",
        "inputs": ["profile", "history", "nextStage"],
        "outputs": ["roleHits", "questionHits", "memoryHits", "retrievalQuality", "toolCalls"],
        "risks": ["empty_retrieval", "weak_retrieval"],
    },
    {
        "name": "analyze_answer",
        "title": "分析上一轮回答",
        "inputs": ["history", "answer"],
        "outputs": ["answerAnalysis", "answerStatus"],
        "risks": ["weak_answer_streak"],
    },
    {
        "name": "apply_policy",
        "title": "应用 Agent 策略",
        "inputs": ["answerAnalysis", "retrievalQuality", "agentMode"],
        "outputs": ["policy", "triggerRules"],
        "risks": ["topic_lock", "requires_human_review"],
    },
    {
        "name": "decide_action",
        "title": "生成下一步决策",
        "inputs": ["agentState", "policy"],
        "outputs": ["decision"],
        "risks": ["invalid_decision"],
    },
    {
        "name": "human_review",
        "title": "人工复核",
        "inputs": ["policy", "decision", "answerAnalysis"],
        "outputs": ["interrupt", "resumeDecision"],
        "risks": ["requires_human_review"],
    },
    {
        "name": "generate_question",
        "title": "生成下一题",
        "inputs": ["decision", "retrievalContext", "history"],
        "outputs": ["nextQuestion"],
        "risks": ["empty_question", "repeated_question"],
    },
    {
        "name": "update_memory",
        "title": "更新候选人记忆",
        "inputs": ["history", "answerAnalysis", "decision"],
        "outputs": ["memoryUpdate"],
        "risks": [],
    },
]


def get_node_contracts() -> list[dict[str, Any]]:
    return [dict(item) for item in NODE_CONTRACTS]


def validate_node_trace(node_trace: list[dict[str, Any]] | None) -> dict[str, Any]:
    known = {item["name"] for item in NODE_CONTRACTS}
    known_nodes: list[str] = []
    unknown_nodes: list[str] = []

    for item in node_trace or []:
        node = str(item.get("node") or item.get("nodeName") or "").strip()
        if not node:
            continue
        if node in known:
            known_nodes.append(node)
        else:
            unknown_nodes.append(node)

    return {
        "valid": not unknown_nodes,
        "knownNodes": known_nodes,
        "unknownNodes": unknown_nodes,
    }
