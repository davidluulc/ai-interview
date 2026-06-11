import json
import math
import re
from typing import Any

from sqlalchemy.orm import Session

from .config import ROOT_DIR
from .rag_store import normalize_metadata_filter
from .retrieval_service import retrieve_chunks, retrieve_multi_query_chunks

QUESTION_BANK_PATH = ROOT_DIR / "data" / "question_bank_seed.json"


def load_question_bank() -> list[dict[str, Any]]:
    if not QUESTION_BANK_PATH.exists():
        return []

    return json.loads(QUESTION_BANK_PATH.read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    return str(value or "").lower()


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_+#.\-]+|[\u4e00-\u9fff]{2,}", text.lower())
    seen = set()
    result = []
    for token in tokens:
        if token not in seen:
            result.append(token)
            seen.add(token)
    return result


def build_question_query(profile: dict[str, Any], stage: str = "") -> str:
    return " ".join(
        [
            str(profile.get("targetRole") or ""),
            str(profile.get("positionTag") or ""),
            str(profile.get("resume") or ""),
            str(profile.get("jd") or ""),
            str(profile.get("company") or ""),
            stage,
        ]
    )


def build_question_metadata_filter(profile: dict[str, Any]) -> dict[str, Any]:
    return normalize_metadata_filter(
        {
            "positionTag": profile.get("positionTag"),
            "difficulty": profile.get("difficulty"),
        }
    )


def question_search_text(item: dict[str, Any]) -> str:
    return " ".join(
        [
            str(item.get("category") or ""),
            str(item.get("position_tag") or ""),
            str(item.get("difficulty") or ""),
            str(item.get("question") or ""),
            str(item.get("reference_answer") or ""),
            " ".join(item.get("key_points", [])),
            " ".join(item.get("tags", [])),
        ]
    ).lower()


def stage_category_bonus(category: str, stage: str) -> float:
    stage_text = normalize_text(stage)
    category_text = normalize_text(category)
    mapping = {
        "project": ["项目", "简历", "职责", "背景", "难点"],
        "technical": ["技术", "系统", "基础", "追问"],
        "behavioral": ["行为", "协作", "压力"],
        "system_design": ["系统设计", "架构"],
    }
    for mapped_category, stage_keywords in mapping.items():
        if category_text == mapped_category and any(keyword in stage_text for keyword in stage_keywords):
            return 3.0
    return 0.0


def score_question(item: dict[str, Any], query: str, tokens: list[str], position_tag: str, stage: str) -> dict[str, Any]:
    text = question_search_text(item)
    query_lower = normalize_text(query)
    matched_tags: list[str] = []
    matchedTokens: list[str] = []
    score = 0.0

    item_position = normalize_text(item.get("position_tag"))
    if position_tag and item_position == normalize_text(position_tag):
        score += 6.0
    elif item_position == "general":
        score += 1.0

    score += stage_category_bonus(str(item.get("category") or ""), stage)

    for tag in item.get("tags", []):
        tag_text = normalize_text(tag)
        if tag_text and tag_text in query_lower:
            matched_tags.append(str(tag))
            score += 4.0

    for point in item.get("key_points", []):
        point_text = normalize_text(point)
        if point_text and point_text in query_lower:
            score += 2.0

    for token in tokens:
        if token and token in text:
            matchedTokens.append(token)
            score += 1.0 + math.log(1 + text.count(token))

    return {
        "score": round(score, 2),
        "matchedTags": matched_tags,
        "matchedTokens": matchedTokens[:8],
    }


def convert_database_question_hit(hit: dict[str, Any]) -> dict[str, Any]:
    metadata = hit.get("metadata") or {}
    return {
        "source": "database",
        "chunkId": hit.get("chunkId"),
        "documentId": hit.get("documentId"),
        "category": metadata.get("category") or "custom",
        "position_tag": metadata.get("positionTag") or metadata.get("position_tag") or "custom",
        "difficulty": metadata.get("difficulty") or "custom",
        "question": hit.get("content") or hit.get("title") or "",
        "reference_answer": metadata.get("referenceAnswer") or "",
        "key_points": metadata.get("keyPoints") or [],
        "tags": metadata.get("tags") or [],
        "score": hit.get("score"),
        "matchedTags": hit.get("matchedKeywords") or [],
        "matchedTokens": hit.get("matchedTokens") or [],
        "retrievalMode": hit.get("retrievalMode") or "bm25",
        "metadataFilter": hit.get("metadataFilter") or {},
        "metadataMatch": bool(hit.get("metadataMatch")) if "metadataMatch" in hit else True,
        "matchedQueryVariant": hit.get("matchedQueryVariant") or "",
        "queryVariants": hit.get("queryVariants") or [],
    }


def retrieve_questions(
    profile: dict[str, Any],
    stage: str = "",
    limit: int = 3,
    db: Session | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    query = build_question_query(profile, stage)
    tokens = tokenize(query)
    position_tag = str(profile.get("positionTag") or "")

    if db is not None and user_id is not None:
        metadata_filter = build_question_metadata_filter(profile)
        database_hits = retrieve_multi_query_chunks(
            db,
            user_id=user_id,
            knowledge_base="question_bank",
            query=query,
            profile=profile,
            stage=stage,
            limit=limit,
            metadata_filter=metadata_filter,
        )
        if not database_hits and metadata_filter:
            database_hits = retrieve_multi_query_chunks(
                db,
                user_id=user_id,
                knowledge_base="question_bank",
                query=query,
                profile=profile,
                stage=stage,
                limit=limit,
            )
        if database_hits:
            return [convert_database_question_hit(hit) for hit in database_hits]

    scored = []

    for item in load_question_bank():
        evidence = score_question(item, query, tokens, position_tag, stage)
        if evidence["score"] <= 0:
            continue

        scored.append(
            {
                **item,
                "score": evidence["score"],
                "matchedTags": evidence["matchedTags"],
                "matchedTokens": evidence["matchedTokens"],
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


def format_question_context(items: list[dict[str, Any]]) -> str:
    if not items:
        return "暂无题库 RAG 上下文。"

    blocks = []
    for index, item in enumerate(items, start=1):
        key_points = "；".join(item.get("key_points", [])) or "暂无"
        matched = "、".join(item.get("matchedTags") or item.get("matchedTokens") or []) or "无"
        blocks.append(
            f"{index}. [{item.get('category')} / {item.get('difficulty')}] {item.get('question')}\n"
            f"   命中分数：{item.get('score')}；命中词：{matched}\n"
            f"   参考答案：{item.get('reference_answer') or '暂无'}\n"
            f"   答题要点：{key_points}"
        )

    return "\n".join(blocks)
