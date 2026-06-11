from typing import Any


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", []):
            return value
    return None


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [str(value)]


def normalize_rag_hit_metadata(hit: dict[str, Any], *, retriever_name: str = "") -> dict[str, Any]:
    raw_metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    knowledge_base = _first_non_empty(
        raw_metadata.get("knowledgeBase"),
        raw_metadata.get("knowledge_base"),
        hit.get("knowledgeBase"),
        hit.get("knowledge_base"),
        retriever_name,
    )
    source = _first_non_empty(raw_metadata.get("source"), hit.get("source"))
    tags = _first_non_empty(
        raw_metadata.get("tags"),
        raw_metadata.get("keywords"),
        hit.get("tags"),
        hit.get("matchedTags"),
        hit.get("matchedKeywords"),
    )

    return {
        "knowledgeBase": str(knowledge_base or ""),
        "documentId": _first_non_empty(raw_metadata.get("documentId"), raw_metadata.get("document_id"), hit.get("documentId")),
        "chunkId": _first_non_empty(raw_metadata.get("chunkId"), raw_metadata.get("chunk_id"), hit.get("chunkId")),
        "title": str(_first_non_empty(raw_metadata.get("title"), hit.get("title"), hit.get("question"), "") or ""),
        "source": str(source or ("database" if hit.get("chunkId") else "seed_json")),
        "ownerUserId": _first_non_empty(raw_metadata.get("ownerUserId"), raw_metadata.get("owner_user_id"), hit.get("ownerUserId")),
        "applicationProfileId": _first_non_empty(
            raw_metadata.get("applicationProfileId"),
            raw_metadata.get("application_profile_id"),
            hit.get("applicationProfileId"),
        ),
        "positionTag": str(
            _first_non_empty(
                raw_metadata.get("positionTag"),
                raw_metadata.get("position_tag"),
                hit.get("positionTag"),
                hit.get("position_tag"),
                "",
            )
            or ""
        ),
        "interviewStage": str(
            _first_non_empty(
                raw_metadata.get("interviewStage"),
                raw_metadata.get("interview_stage"),
                hit.get("interviewStage"),
                hit.get("stage"),
                "",
            )
            or ""
        ),
        "difficulty": str(_first_non_empty(raw_metadata.get("difficulty"), hit.get("difficulty"), "") or ""),
        "tags": _as_list(tags),
        "createdAt": _first_non_empty(raw_metadata.get("createdAt"), raw_metadata.get("created_at"), hit.get("createdAt")),
    }


def normalize_rag_hit(hit: dict[str, Any], *, retriever_name: str = "") -> dict[str, Any]:
    metadata = normalize_rag_hit_metadata(hit, retriever_name=retriever_name)
    return {
        "score": hit.get("score"),
        "title": str(hit.get("title") or hit.get("question") or hit.get("targetRole") or metadata.get("title") or ""),
        "content": str(hit.get("content") or hit.get("reference_answer") or ""),
        "matchedKeywords": _as_list(hit.get("matchedKeywords") or hit.get("matchedTags")),
        "matchedTokens": _as_list(hit.get("matchedTokens")),
        "retrievalMode": str(hit.get("retrievalMode") or hit.get("retrieval_mode") or ""),
        "metadata": metadata,
    }


def metadata_matches(
    metadata: dict[str, Any],
    *,
    expected_knowledge_base: str = "",
    expected_position_tag: str = "",
    expected_stage: str = "",
) -> bool:
    if expected_knowledge_base and str(metadata.get("knowledgeBase") or "") != expected_knowledge_base:
        return False
    if expected_position_tag and str(metadata.get("positionTag") or "") != expected_position_tag:
        return False
    if expected_stage and str(metadata.get("interviewStage") or "") != expected_stage:
        return False
    return True

