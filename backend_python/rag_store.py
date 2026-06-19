import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import RagChunk, RagDocument
from .embedding_client import current_embedding_model, embed_text
from .knowledge_bases import VALID_KNOWLEDGE_BASES

DOCUMENT_STATUSES = {"enabled", "disabled", "archived"}
DOCUMENT_VISIBILITIES = {"private", "public"}
METADATA_FILTER_FIELDS = {
    "positionTag": ("positionTag", "position_tag"),
    "category": ("category",),
    "difficulty": ("difficulty",),
    "interviewStage": ("interviewStage", "interview_stage", "stage"),
    "source": ("source", "sourceType", "source_type"),
}


def parse_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return fallback


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def normalize_hash_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def compute_text_hash(value: str) -> str:
    return hashlib.sha256(normalize_hash_text(value).encode("utf-8")).hexdigest()


def build_chunk_hash_records(chunks: list[str]) -> list[dict[str, Any]]:
    seen_hashes: set[str] = set()
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        chunk_hash = compute_text_hash(chunk)
        is_duplicate = chunk_hash in seen_hashes
        seen_hashes.add(chunk_hash)
        records.append(
            {
                "content": chunk,
                "hash": chunk_hash,
                "isDuplicate": is_duplicate,
            }
        )
    return records


def normalize_document_status(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in DOCUMENT_STATUSES else "enabled"


def normalize_document_visibility(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in DOCUMENT_VISIBILITIES else "private"


def normalize_metadata_filter(value: dict[str, Any] | None) -> dict[str, str | list[str]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str | list[str]] = {}
    for canonical_key, aliases in METADATA_FILTER_FIELDS.items():
        raw_value = None
        for alias in aliases:
            if alias in value:
                raw_value = value.get(alias)
                break
        if isinstance(raw_value, list):
            items = [str(item).strip() for item in raw_value if str(item).strip()]
            if items:
                normalized[canonical_key] = items
        elif raw_value not in (None, ""):
            normalized[canonical_key] = str(raw_value).strip()
    return normalized


def metadata_value(metadata: dict[str, Any], canonical_key: str) -> Any:
    for alias in METADATA_FILTER_FIELDS.get(canonical_key, (canonical_key,)):
        value = metadata.get(alias)
        if value not in (None, ""):
            return value
    return None


def chunk_matches_metadata_filter(metadata: dict[str, Any], metadata_filter: dict[str, Any] | None) -> bool:
    normalized_filter = normalize_metadata_filter(metadata_filter)
    if not normalized_filter:
        return True

    for key, expected in normalized_filter.items():
        actual = metadata_value(metadata, key)
        if actual in (None, ""):
            return False
        actual_values = [str(item).strip().lower() for item in actual] if isinstance(actual, list) else [str(actual).strip().lower()]
        expected_values = (
            [str(item).strip().lower() for item in expected]
            if isinstance(expected, list)
            else [str(expected).strip().lower()]
        )
        if not any(expected_value in actual_values for expected_value in expected_values):
            return False
    return True


def split_content_into_chunks(content: str, max_chars: int = 700) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content.strip()) if paragraph.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        for start in range(0, len(paragraph), max_chars):
            chunks.append(paragraph[start : start + max_chars])
    return chunks


def tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9_+#.\-]+|[\u4e00-\u9fff]{2,}", query.lower())
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            unique_tokens.append(token)
            seen.add(token)
    return unique_tokens


def extract_keywords(text: str, limit: int = 12) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_+#.\-]{1,}|[\u4e00-\u9fff]{2,}", text)
    seen = set()
    keywords = []
    for token in tokens:
        normalized = token.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def serialize_document(document: RagDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "title": document.title,
        "knowledgeBase": document.knowledge_base,
        "sourceType": document.source_type,
        "status": normalize_document_status(getattr(document, "status", "enabled")),
        "visibility": normalize_document_visibility(getattr(document, "visibility", "private")),
        "contentHash": getattr(document, "content_hash", "") or compute_text_hash(document.content),
        "content": document.content,
        "metadata": parse_json(document.metadata_json, {}),
        "chunkCount": document.chunk_count,
        "duplicateChunkCount": getattr(document, "duplicate_chunk_count", 0) or 0,
        "createdAt": serialize_datetime(document.created_at),
        "updatedAt": serialize_datetime(document.updated_at),
    }


def serialize_chunk(chunk: RagChunk) -> dict[str, Any]:
    embedding = parse_json(chunk.embedding_json, [])
    return {
        "id": chunk.id,
        "documentId": chunk.document_id,
        "knowledgeBase": chunk.knowledge_base,
        "title": chunk.title,
        "content": chunk.content,
        "chunkIndex": chunk.chunk_index,
        "chunkHash": getattr(chunk, "chunk_hash", "") or compute_text_hash(chunk.content),
        "isDuplicate": bool(getattr(chunk, "is_duplicate", 0)),
        "keywords": parse_json(chunk.keywords_json, []),
        "metadata": parse_json(chunk.metadata_json, {}),
        "embeddingStatus": chunk.embedding_status,
        "embeddingModel": chunk.embedding_model,
        "embeddingSize": len(embedding) if isinstance(embedding, list) else 0,
        "createdAt": serialize_datetime(chunk.created_at),
    }


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def create_rag_document(
    db: Session,
    *,
    user_id: int,
    title: str,
    knowledge_base: str,
    source_type: str,
    content: str,
    metadata: dict[str, Any],
    status: str = "enabled",
    visibility: str = "private",
) -> RagDocument:
    chunks = split_content_into_chunks(content)
    chunk_records = build_chunk_hash_records(chunks)
    document = RagDocument(
        user_id=user_id,
        title=title.strip(),
        knowledge_base=knowledge_base,
        source_type=source_type.strip() or "manual",
        status=normalize_document_status(status),
        visibility=normalize_document_visibility(visibility),
        content_hash=compute_text_hash(content),
        content=content.strip(),
        metadata_json=dump_json(metadata),
        chunk_count=len(chunks),
        duplicate_chunk_count=sum(1 for item in chunk_records if item["isDuplicate"]),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    for index, chunk_record in enumerate(chunk_records):
        chunk_content = str(chunk_record["content"])
        chunk = RagChunk(
            user_id=user_id,
            document_id=document.id,
            knowledge_base=knowledge_base,
            title=document.title,
            content=chunk_content,
            chunk_index=index,
            chunk_hash=str(chunk_record["hash"]),
            is_duplicate=1 if chunk_record["isDuplicate"] else 0,
            keywords_json=dump_json(extract_keywords(f"{document.title} {chunk_content}")),
            metadata_json=document.metadata_json,
        )
        db.add(chunk)
    db.commit()
    db.refresh(document)
    return document


async def create_rag_document_with_embeddings(
    db: Session,
    *,
    user_id: int,
    title: str,
    knowledge_base: str,
    source_type: str,
    content: str,
    metadata: dict[str, Any],
    status: str = "enabled",
    visibility: str = "private",
) -> RagDocument:
    chunks = split_content_into_chunks(content)
    chunk_records = build_chunk_hash_records(chunks)
    document = RagDocument(
        user_id=user_id,
        title=title.strip(),
        knowledge_base=knowledge_base,
        source_type=source_type.strip() or "manual",
        status=normalize_document_status(status),
        visibility=normalize_document_visibility(visibility),
        content_hash=compute_text_hash(content),
        content=content.strip(),
        metadata_json=dump_json(metadata),
        chunk_count=len(chunks),
        duplicate_chunk_count=sum(1 for item in chunk_records if item["isDuplicate"]),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    for index, chunk_record in enumerate(chunk_records):
        chunk_content = str(chunk_record["content"])
        embedding: list[float] = []
        embedding_status = "pending"
        embedding_model = current_embedding_model()
        try:
            embedding = await embed_text(chunk_content)
            embedding_status = "ready" if embedding else "empty"
        except Exception:
            embedding_status = "failed"

        chunk = RagChunk(
            user_id=user_id,
            document_id=document.id,
            knowledge_base=knowledge_base,
            title=document.title,
            content=chunk_content,
            chunk_index=index,
            chunk_hash=str(chunk_record["hash"]),
            is_duplicate=1 if chunk_record["isDuplicate"] else 0,
            keywords_json=dump_json(extract_keywords(f"{document.title} {chunk_content}")),
            metadata_json=document.metadata_json,
            embedding_json=dump_json(embedding),
            embedding_model=embedding_model if embedding_status == "ready" else "",
            embedding_status=embedding_status,
        )
        db.add(chunk)
    db.commit()
    db.refresh(document)
    return document


def chunk_search_text(chunk: RagChunk) -> str:
    keywords = " ".join(parse_json(chunk.keywords_json, []))
    metadata = " ".join(str(value) for value in parse_json(chunk.metadata_json, {}).values())
    return f"{chunk.title} {chunk.content} {keywords} {metadata}".lower()


def score_chunk(chunk: RagChunk, query: str, tokens: list[str]) -> dict[str, Any]:
    text = chunk_search_text(chunk)
    query_lower = query.lower()
    keywords = parse_json(chunk.keywords_json, [])
    matched_keywords = []
    matched_tokens = []
    score = 0.0

    for keyword in keywords:
        keyword_text = str(keyword).lower()
        if keyword_text and keyword_text in query_lower:
            matched_keywords.append(str(keyword))
            score += 5.0

    for token in tokens:
        if token and token in text:
            matched_tokens.append(token)
            score += 1.2 + math.log(1 + text.count(token))

    return {
        "score": round(score, 2),
        "matchedKeywords": matched_keywords,
        "matchedTokens": matched_tokens[:8],
    }


def retrieve_database_chunks(
    db: Session,
    *,
    user_id: int,
    knowledge_base: str,
    query: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    tokens = tokenize_query(query)
    statement = (
        select(RagChunk)
        .where(RagChunk.user_id == user_id, RagChunk.knowledge_base == knowledge_base)
        .order_by(RagChunk.created_at.desc(), RagChunk.id.desc())
        .limit(80)
    )
    scored = []
    for chunk in db.scalars(statement).all():
        evidence = score_chunk(chunk, query, tokens)
        if evidence["score"] <= 0:
            continue
        metadata = parse_json(chunk.metadata_json, {})
        scored.append(
            {
                "source": "database",
                "chunkId": chunk.id,
                "documentId": chunk.document_id,
                "title": chunk.title,
                "content": chunk.content,
                "score": evidence["score"],
                "matchedKeywords": evidence["matchedKeywords"],
                "matchedTokens": evidence["matchedTokens"],
                "metadata": metadata,
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]
