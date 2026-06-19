from typing import Any

from .knowledge_bases import KNOWLEDGE_BASE_LABELS
from .rag_metadata import normalize_rag_hit

RETRIEVER_LABELS = KNOWLEDGE_BASE_LABELS


def retriever_label(retriever_name: str) -> str:
    return RETRIEVER_LABELS.get(str(retriever_name or ""), str(retriever_name or "RAG"))


def build_user_rag_reason(*, retriever_name: str, hits: list[dict[str, Any]], focus: str = "") -> str:
    label = retriever_label(retriever_name)
    focus_text = str(focus or "当前考察点").strip()
    if not hits:
        return f"围绕「{focus_text}」追问时，暂无{label}命中，系统会更多依赖简历、JD 和历史回答做兜底。"

    top_hit = normalize_rag_hit(hits[0], retriever_name=retriever_name)
    matched = top_hit.get("matchedTokens") or top_hit.get("matchedKeywords") or []
    matched_text = "、".join(str(item) for item in matched[:4]) or "未记录命中词"
    title = top_hit.get("title") or "未命名资料"
    return f"这道题围绕「{focus_text}」展开，主要参考了{label}中的「{title}」，命中词包括：{matched_text}。"


def _normalize_relevance_text(value: str) -> str:
    return str(value or "").lower().replace("_", "").replace("-", "")


def _hit_matches_question(hit: dict[str, Any], *, focus: str, prompt: str) -> bool:
    question_text = _normalize_relevance_text(f"{focus} {prompt}")
    normalized_hit = normalize_rag_hit(hit, retriever_name="")
    hit_text = _normalize_relevance_text(
        " ".join(
            [
                str(normalized_hit.get("title") or ""),
                str(normalized_hit.get("content") or ""),
                " ".join(str(item) for item in normalized_hit.get("matchedTokens") or []),
                " ".join(str(item) for item in normalized_hit.get("matchedKeywords") or []),
            ]
        )
    )
    if not question_text or not hit_text:
        return False
    for token in normalized_hit.get("matchedTokens") or normalized_hit.get("matchedKeywords") or []:
        normalized_token = _normalize_relevance_text(str(token))
        if len(normalized_token) >= 2 and normalized_token in question_text:
            return True
    important_terms = ("rag", "bm25", "vector", "向量", "召回", "日志", "命中", "retrieval", "matchedretrievalmodes")
    return any(term in question_text and term in hit_text for term in important_terms)


def build_relevant_user_rag_reason(
    *,
    retriever_name: str,
    hits: list[dict[str, Any]],
    focus: str = "",
    prompt: str = "",
) -> str | None:
    if not hits:
        return None
    relevant_hits = [hit for hit in hits if _hit_matches_question(hit, focus=focus, prompt=prompt)]
    if not relevant_hits:
        return None
    return build_user_rag_reason(retriever_name=retriever_name, hits=relevant_hits, focus=focus)


def build_developer_rag_debug_summary(
    *,
    query_text: str,
    retriever_name: str,
    retrieval_mode: str,
    hits: list[dict[str, Any]],
    used_in_prompt: bool,
    limit: int = 5,
) -> dict[str, Any]:
    normalized_hits = [normalize_rag_hit(hit, retriever_name=retriever_name) for hit in hits[:limit]]
    return {
        "queryText": str(query_text or ""),
        "retrieverName": str(retriever_name or ""),
        "retrieverLabel": retriever_label(retriever_name),
        "retrievalMode": str(retrieval_mode or ""),
        "hitCount": len(hits),
        "usedInPrompt": bool(used_in_prompt),
        "hits": normalized_hits,
    }


def build_rag_debug_explanation(
    *,
    retriever_name: str,
    hits: list[dict[str, Any]],
    quality: dict[str, Any],
    limit: int = 3,
) -> dict[str, Any]:
    normalized_hits = [normalize_rag_hit(hit, retriever_name=retriever_name) for hit in hits[:limit]]
    matched_terms: list[str] = []
    for hit in normalized_hits:
        for key in ("matchedTokens", "matchedKeywords"):
            for item in hit.get(key) or []:
                text = str(item).strip()
                if text and text not in matched_terms:
                    matched_terms.append(text)
        for item in hit.get("metadata", {}).get("tags") or []:
            text = str(item).strip()
            if text and text not in matched_terms:
                matched_terms.append(text)

    top_titles = [
        str(hit.get("title") or hit.get("question") or "未命名命中")
        for hit in normalized_hits
    ]
    label = retriever_label(retriever_name)
    quality_label = str(quality.get("label") or "未评估")

    return {
        "retrieverName": str(retriever_name or ""),
        "retrieverLabel": label,
        "hitCount": len(hits),
        "qualityLevel": str(quality.get("level") or "miss"),
        "qualityLabel": quality_label,
        "qualityReason": str(quality.get("reason") or "暂无质量说明"),
        "topTitles": top_titles,
        "matchedTerms": matched_terms[:8],
        "developerSummary": (
            f"{label}命中 {len(hits)} 条，质量为{quality_label}，"
            f"主要命中：{'、'.join(top_titles[:2]) or '暂无'}。"
        ),
    }
