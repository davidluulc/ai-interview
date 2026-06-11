import json
import math
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from .config import ROOT_DIR
from .rag_store import normalize_metadata_filter
from .retrieval_service import retrieve_chunks, retrieve_multi_query_chunks

KNOWLEDGE_PATH = ROOT_DIR / "data" / "role_knowledge_seed.json"


def load_role_knowledge() -> list[dict[str, Any]]:
    if not KNOWLEDGE_PATH.exists():
        return []

    return json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    return str(value or "").lower()


def tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_+#.\-]+|[\u4e00-\u9fff]{2,}", query.lower())
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            unique_tokens.append(token)
            seen.add(token)
    return unique_tokens


def build_role_query(profile: dict[str, Any], next_stage: str = "") -> str:
    return " ".join(
        [
            str(profile.get("targetRole") or ""),
            str(profile.get("resume") or ""),
            str(profile.get("jd") or ""),
            str(profile.get("company") or ""),
            next_stage,
        ]
    )


def build_role_metadata_filter(profile: dict[str, Any]) -> dict[str, Any]:
    return normalize_metadata_filter({"positionTag": profile.get("positionTag")})


def item_search_text(item: dict[str, Any]) -> str:
    values: list[str] = [
        str(item.get("role") or ""),
        str(item.get("category") or ""),
        str(item.get("title") or ""),
        str(item.get("content") or ""),
    ]
    values.extend(str(keyword) for keyword in item.get("keywords", []))
    values.extend(str(point) for point in item.get("scoring_points", []))
    values.extend(str(question) for question in item.get("follow_up_questions", []))
    values.extend(str(signal) for signal in item.get("risk_signals", []))
    return " ".join(values).lower()


def score_item(item: dict[str, Any], query: str, tokens: list[str]) -> dict[str, Any]:
    text = item_search_text(item)
    query_lower = normalize_text(query)
    matched_keywords: list[str] = []
    matched_tokens: list[str] = []
    score = 0.0

    for keyword in item.get("keywords", []):
        keyword_text = normalize_text(keyword)
        if keyword_text and keyword_text in query_lower:
            matched_keywords.append(str(keyword))
            score += 5.0

    for token in tokens:
        if token and token in text:
            matched_tokens.append(token)
            token_frequency = text.count(token)
            score += 1.5 + math.log(1 + token_frequency)

    role = normalize_text(item.get("role"))
    target_role = normalize_text(query)
    if role == "通用":
        score += 0.5
    elif role and role in target_role:
        score += 2.0

    category = normalize_text(item.get("category"))
    title = normalize_text(item.get("title"))
    if category and category in query_lower:
        score += 1.0
    if title and title in query_lower:
        score += 1.0

    return {
        "score": round(score, 2),
        "matchedKeywords": matched_keywords,
        "matchedTokens": matched_tokens[:8],
    }


def convert_database_role_hit(hit: dict[str, Any]) -> dict[str, Any]:
    metadata = hit.get("metadata") or {}
    return {
        "source": "database",
        "chunkId": hit.get("chunkId"),
        "documentId": hit.get("documentId"),
        "role": metadata.get("role") or metadata.get("targetRole") or "自定义知识库",
        "category": metadata.get("category") or "custom",
        "title": hit.get("title") or "自定义岗位知识",
        "content": hit.get("content") or "",
        "keywords": hit.get("matchedKeywords") or [],
        "scoring_points": metadata.get("scoringPoints") or [],
        "follow_up_questions": metadata.get("followUpQuestions") or [],
        "risk_signals": metadata.get("riskSignals") or [],
        "score": hit.get("score"),
        "matchedKeywords": hit.get("matchedKeywords") or [],
        "matchedTokens": hit.get("matchedTokens") or [],
        "retrievalMode": hit.get("retrievalMode") or "bm25",
        "metadataFilter": hit.get("metadataFilter") or {},
        "metadataMatch": bool(hit.get("metadataMatch")) if "metadataMatch" in hit else True,
        "matchedQueryVariant": hit.get("matchedQueryVariant") or "",
        "queryVariants": hit.get("queryVariants") or [],
    }


def retrieve_role_context(
    profile: dict[str, Any],
    next_stage: str = "",
    limit: int = 3,
    db: Session | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    query = build_role_query(profile, next_stage)
    tokens = tokenize_query(query)

    if db is not None and user_id is not None:
        metadata_filter = build_role_metadata_filter(profile)
        database_hits = retrieve_multi_query_chunks(
            db,
            user_id=user_id,
            knowledge_base="role_knowledge",
            query=query,
            profile=profile,
            stage=next_stage,
            limit=limit,
            metadata_filter=metadata_filter,
        )
        if not database_hits and metadata_filter:
            database_hits = retrieve_multi_query_chunks(
                db,
                user_id=user_id,
                knowledge_base="role_knowledge",
                query=query,
                profile=profile,
                stage=next_stage,
                limit=limit,
            )
        if database_hits:
            return [convert_database_role_hit(hit) for hit in database_hits]

    scored = []
    for item in load_role_knowledge():
        evidence = score_item(item, query, tokens)
        if evidence["score"] > 0:
            enriched_item = {
                **item,
                "score": evidence["score"],
                "matchedKeywords": evidence["matchedKeywords"],
                "matchedTokens": evidence["matchedTokens"],
            }
            scored.append(enriched_item)

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


def format_role_context(items: list[dict[str, Any]]) -> str:
    if not items:
        return "暂无岗位知识库上下文。"

    blocks = []
    for index, item in enumerate(items, start=1):
        scoring_points = "；".join(item.get("scoring_points", [])) or "暂无"
        follow_ups = "；".join(item.get("follow_up_questions", [])[:2]) or "暂无"
        risk_signals = "；".join(item.get("risk_signals", [])[:2]) or "暂无"
        matched = "、".join(item.get("matchedKeywords") or item.get("matchedTokens") or []) or "无"
        blocks.append(
            f"{index}. [{item.get('category')}] {item.get('title')}\n"
            f"   命中分数：{item.get('score')}；命中词：{matched}\n"
            f"   资料内容：{item.get('content')}\n"
            f"   可追问方向：{follow_ups}\n"
            f"   评分点：{scoring_points}\n"
            f"   风险信号：{risk_signals}"
        )

    return "\n".join(blocks)
