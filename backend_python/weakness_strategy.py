from typing import Any

TAG_LABELS = {
    "rag_retrieval": "RAG 召回链路",
    "rag_quality": "RAG 质量评估",
    "agent_state": "Agent State",
    "backend_fastapi": "FastAPI 后端模块",
    "database_modeling": "数据库建模",
    "deployment_readiness": "上线部署准备",
    "project_storytelling": "项目讲解",
    "communication_expression": "表达沟通",
}

TAG_KEYWORDS = {
    "rag_retrieval": ("rag", "召回", "检索", "query", "rewrite", "chunk"),
    "rag_quality": ("rag", "质量", "Hit@K", "MRR", "关键词覆盖率", "命中", "评估"),
    "agent_state": ("agent", "state", "tool", "decision", "orchestrator", "决策", "状态"),
    "backend_fastapi": ("fastapi", "router", "schema", "接口", "后端", "模块"),
    "database_modeling": ("sqlalchemy", "mysql", "数据库", "外键", "relationship", "表"),
    "deployment_readiness": ("docker", "nginx", "uvicorn", "redis", "部署", "上线"),
    "project_storytelling": ("项目", "背景", "职责", "难点", "结果", "简历"),
    "communication_expression": ("表达", "沟通", "行为", "规划", "薪资"),
}

WEAK_TEXT_MARKERS = ("不会", "不知道", "写不出来", "不清楚", "不了解", "没接触")


def normalize_weak_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    for item in value:
        tag = str(item or "").strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _context_text(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, dict):
            parts.extend(str(item or "") for item in value.values())
        elif isinstance(value, list):
            parts.extend(_context_text(item) for item in value)
        else:
            parts.append(str(value or ""))
    return " ".join(parts).lower()


def _tag_matches_context(tag: str, context: str) -> bool:
    label = TAG_LABELS.get(tag, tag)
    if label.lower() in context or tag.lower() in context:
        return True
    return any(keyword.lower() in context for keyword in TAG_KEYWORDS.get(tag, ()))


def _count_recent_weak_tag(history: list[dict[str, Any]], tag: str, window_size: int = 2) -> int:
    count = 0
    for item in list(history or [])[-window_size:]:
        item_tags = normalize_weak_tags(item.get("weakTags"))
        focus_text = _context_text(item.get("focus"), item.get("question"))
        if tag in item_tags or _tag_matches_context(tag, focus_text):
            answer = str(item.get("answer") or "")
            if not answer.strip() or any(marker in answer for marker in WEAK_TEXT_MARKERS):
                count += 1
    return count


def _disabled_strategy() -> dict[str, Any]:
    return {
        "enabled": False,
        "matchedWeakTags": [],
        "primaryWeakTag": "",
        "primaryWeakLabel": "",
        "modePolicy": "none",
        "recommendedAction": "",
        "recommendedDifficulty": "",
        "reason": "候选人画像中暂无高频薄弱标签，本轮保持常规 Agent 决策。",
        "triggerRules": [],
        "guardrailApplied": False,
    }


def select_weakness_strategy(
    *,
    candidate_profile: dict[str, Any],
    agent_mode: str,
    profile: dict[str, Any],
    next_stage: str,
    history: list[dict[str, Any]],
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
    answer_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frequent_tags = normalize_weak_tags(candidate_profile.get("frequentWeakTags"))
    if not frequent_tags:
        return _disabled_strategy()

    context = _context_text(profile, next_stage, history[-2:], role_hits, question_hits, memory_hits)
    matched_tags = [tag for tag in frequent_tags if _tag_matches_context(tag, context)]
    primary_tag = matched_tags[0] if matched_tags else frequent_tags[0]
    primary_label = TAG_LABELS.get(primary_tag, primary_tag)
    mode = "coach" if agent_mode == "coach" else "interview"
    weak_streak = int((answer_analysis or {}).get("weakAnswerStreak") or 0)
    recent_tag_weak_count = _count_recent_weak_tag(history, primary_tag)
    selected_tags = matched_tags or [primary_tag]

    if weak_streak >= 2 and recent_tag_weak_count >= 2:
        return {
            "enabled": True,
            "matchedWeakTags": selected_tags,
            "primaryWeakTag": primary_tag,
            "primaryWeakLabel": primary_label,
            "modePolicy": "avoid_weakness_deadlock",
            "recommendedAction": "switch_topic",
            "recommendedDifficulty": "basic",
            "reason": f"候选人已连续在「{primary_label}」相关问题上回答偏弱，本轮触发防死磕策略，避免继续卡同一个薄弱点。",
            "triggerRules": ["weakness_strategy", "weakness_deadlock_guardrail"],
            "guardrailApplied": True,
        }

    if mode == "coach":
        return {
            "enabled": True,
            "matchedWeakTags": selected_tags,
            "primaryWeakTag": primary_tag,
            "primaryWeakLabel": primary_label,
            "modePolicy": "coach_remediation",
            "recommendedAction": "practice_weakness",
            "recommendedDifficulty": "basic",
            "reason": f"候选人画像显示「{primary_label}」是高频薄弱点，当前为学习辅导模式，本轮优先拆小问题并补基础。",
            "triggerRules": ["weakness_strategy", "coach_weakness_remediation"],
            "guardrailApplied": False,
        }

    return {
        "enabled": True,
        "matchedWeakTags": selected_tags,
        "primaryWeakTag": primary_tag,
        "primaryWeakLabel": primary_label,
        "modePolicy": "interview_probe",
        "recommendedAction": "deep_follow_up",
        "recommendedDifficulty": "medium",
        "reason": f"候选人画像显示「{primary_label}」是高频薄弱点，当前为真实面试模式，本轮适度围绕该点追问但保留话题切换保护。",
        "triggerRules": ["weakness_strategy", "interview_weakness_probe"],
        "guardrailApplied": False,
    }
