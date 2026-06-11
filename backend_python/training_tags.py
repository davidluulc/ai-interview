from typing import Any


WEAK_TAG_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rag_retrieval", ("rag", "召回", "检索", "知识库", "chunk", "切片", "retrieval")),
    ("rag_quality", ("hit@k", "mrr", "关键词覆盖率", "质量评估", "命中日志", "quality", "rerank")),
    ("agent_state", ("agent state", "agent", "状态", "决策", "orchestrator", "nodeTrace", "toolCalls")),
    ("backend_fastapi", ("fastapi", "router", "路由", "schema", "接口", "后端模块")),
    ("database_modeling", ("sqlalchemy", "model", "数据库", "表结构", "外键", "relationship", "索引")),
    ("deployment_readiness", ("docker", "nginx", "uvicorn", "redis", "部署", "上线", "环境变量")),
    ("project_storytelling", ("项目背景", "项目职责", "项目经历", "真实性", "负责")),
)


def _normalize_text(*values: Any) -> str:
    return " ".join(str(value or "").lower() for value in values)


def infer_weak_tags(*, focus: str = "", text: str = "", limit: int = 4) -> list[str]:
    source = _normalize_text(focus, text)
    tags: list[str] = []
    for tag, keywords in WEAK_TAG_RULES:
        if any(keyword.lower() in source for keyword in keywords):
            tags.append(tag)
        if len(tags) >= limit:
            break
    return tags or ["communication_expression"]


def merge_weak_tags(*values: Any, focus: str = "", text: str = "", limit: int = 4) -> list[str]:
    merged: list[str] = []
    for value in values:
        if isinstance(value, list):
            candidates = value
        elif value in (None, ""):
            candidates = []
        else:
            candidates = [value]
        for item in candidates:
            tag = str(item or "").strip()
            if tag and tag not in merged:
                merged.append(tag)

    for tag in infer_weak_tags(focus=focus, text=text, limit=limit):
        if tag not in merged:
            merged.append(tag)
        if len(merged) >= limit:
            break
    return merged[:limit] or ["communication_expression"]
