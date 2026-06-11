import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import RagRetrievalLog
from .rag_metadata import normalize_rag_hit
from .rag_quality import evaluate_retrieval_quality


def build_rag_query(profile: dict[str, Any], stage: str, extra_text: str = "") -> str:
    parts = [
        profile.get("candidateName"),
        profile.get("targetRole"),
        profile.get("positionTag"),
        profile.get("resume"),
        profile.get("jd"),
        profile.get("company"),
        stage,
        extra_text,
    ]
    return " ".join(str(part or "") for part in parts).strip()[:1200]


def summarize_hit(hit: dict[str, Any], *, retriever_name: str = "") -> dict[str, Any]:
    normalized = normalize_rag_hit(hit, retriever_name=retriever_name)
    summary = {
        "score": hit.get("score"),
        "title": hit.get("title") or hit.get("question") or hit.get("targetRole") or "",
        "content": normalized.get("content") or "",
        "positionTag": hit.get("position_tag") or hit.get("positionTag") or "",
        "category": hit.get("category") or "",
        "difficulty": hit.get("difficulty") or "",
        "source": hit.get("source") or ("database" if hit.get("chunkId") else "seed"),
        "chunkId": hit.get("chunkId"),
        "documentId": hit.get("documentId"),
        "matchedKeywords": hit.get("matchedKeywords") or hit.get("matchedTags") or [],
        "matchedTokens": hit.get("matchedTokens") or [],
        "metadata": normalized["metadata"],
        "retrievalMode": hit.get("retrievalMode") or hit.get("retrieval_mode") or "",
        "matchedRetrievalModes": hit.get("matchedRetrievalModes") or [],
        "hybridScore": hit.get("hybridScore"),
        "bm25Score": hit.get("bm25Score"),
        "vectorScore": hit.get("vectorScore"),
        "rerankScore": hit.get("rerankScore"),
        "rerankIndex": hit.get("rerankIndex"),
        "preRerankRank": hit.get("preRerankRank"),
    }
    return {key: value for key, value in summary.items() if value not in ("", [], None)}


def serialize_hits(hits: list[dict[str, Any]], limit: int = 5, retriever_name: str = "") -> str:
    return json.dumps([summarize_hit(hit, retriever_name=retriever_name) for hit in hits[:limit]], ensure_ascii=False)


def infer_retrieval_mode(hits: list[dict[str, Any]], fallback: str = "keyword") -> str:
    for hit in hits:
        mode = hit.get("retrievalMode") or hit.get("retrieval_mode")
        if mode:
            return str(mode)
    return fallback


def create_rag_log(
    db: Session,
    *,
    user_id: int,
    application_profile_id: int | None,
    interview_record_id: int | None = None,
    request_type: str,
    query_text: str,
    retriever_name: str,
    hits: list[dict[str, Any]],
    retrieval_mode: str = "keyword",
    used_in_prompt: bool = True,
) -> RagRetrievalLog:
    log = RagRetrievalLog(
        user_id=user_id,
        application_profile_id=application_profile_id,
        interview_record_id=interview_record_id,
        request_type=request_type,
        query_text=query_text,
        retriever_name=retriever_name,
        retrieval_mode=retrieval_mode,
        hit_count=len(hits),
        hits_json=serialize_hits(hits, retriever_name=retriever_name),
        used_in_prompt=1 if used_in_prompt else 0,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def serialize_rag_log(log: RagRetrievalLog) -> dict[str, Any]:
    hits = json.loads(log.hits_json or "[]")
    return {
        "id": log.id,
        "userId": log.user_id,
        "applicationProfileId": log.application_profile_id,
        "interviewRecordId": log.interview_record_id,
        "requestType": log.request_type,
        "queryText": log.query_text,
        "retrieverName": log.retriever_name,
        "retrievalMode": log.retrieval_mode,
        "hitCount": log.hit_count,
        "hits": hits,
        "quality": evaluate_retrieval_quality(hits),
        "usedInPrompt": bool(log.used_in_prompt),
        "createdAt": log.created_at.isoformat() if log.created_at else None,
    }


def list_recent_rag_logs(
    db: Session,
    *,
    user_id: int,
    request_type: str = "",
    limit: int = 20,
) -> list[RagRetrievalLog]:
    statement = select(RagRetrievalLog).where(RagRetrievalLog.user_id == user_id)
    if request_type:
        statement = statement.where(RagRetrievalLog.request_type == request_type)
    return db.scalars(statement.order_by(RagRetrievalLog.created_at.desc(), RagRetrievalLog.id.desc()).limit(limit)).all()
