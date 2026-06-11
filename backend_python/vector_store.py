import json
import math
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .db_models import RagChunk, RagDocument
from .rag_store import chunk_matches_metadata_filter, dump_json, parse_json


@dataclass(frozen=True)
class VectorSearchResult:
    chunk_id: int
    document_id: int
    knowledge_base: str
    title: str
    content: str
    score: float
    metadata: dict[str, Any]
    embedding_model: str
    document_status: str
    document_visibility: str
    owner_user_id: int


class VectorStore(Protocol):
    def upsert_embedding(self, *, chunk_id: int, embedding: list[float], model: str) -> None:
        ...

    def search(
        self,
        *,
        user_id: int,
        knowledge_base: str,
        query_embedding: list[float],
        limit: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        ...


def parse_embedding(value: str) -> list[float]:
    try:
        embedding = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(embedding, list):
        return []
    try:
        return [float(item) for item in embedding]
    except (TypeError, ValueError):
        return []


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return round(dot_product / (left_norm * right_norm), 4)


class SQLiteVectorStore:
    def __init__(self, db: Session):
        self.db = db

    def upsert_embedding(self, *, chunk_id: int, embedding: list[float], model: str) -> None:
        chunk = self.db.get(RagChunk, chunk_id)
        if not chunk:
            return
        chunk.embedding_json = dump_json(embedding)
        chunk.embedding_model = model
        chunk.embedding_status = "ready" if embedding else "empty"
        self.db.add(chunk)
        self.db.commit()

    def search(
        self,
        *,
        user_id: int,
        knowledge_base: str,
        query_embedding: list[float],
        limit: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        if not query_embedding:
            return []
        chunks = self.db.scalars(
            select(RagChunk)
            .join(RagDocument, RagChunk.document_id == RagDocument.id)
            .where(
                RagChunk.knowledge_base == knowledge_base,
                RagChunk.embedding_status == "ready",
                RagDocument.status == "enabled",
                or_(RagDocument.user_id == user_id, RagDocument.visibility == "public"),
            )
            .order_by(RagChunk.created_at.desc(), RagChunk.id.desc())
            .limit(200)
        ).all()

        results: list[VectorSearchResult] = []
        for chunk in chunks:
            metadata = parse_json(chunk.metadata_json, {})
            if not chunk_matches_metadata_filter(metadata, metadata_filter):
                continue
            score = cosine_similarity(query_embedding, parse_embedding(chunk.embedding_json))
            if score <= 0:
                continue
            document = chunk.document
            results.append(
                VectorSearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    knowledge_base=chunk.knowledge_base,
                    title=chunk.title,
                    content=chunk.content,
                    score=score,
                    metadata=metadata,
                    embedding_model=chunk.embedding_model,
                    document_status=getattr(document, "status", "") or "enabled",
                    document_visibility=getattr(document, "visibility", "") or "private",
                    owner_user_id=document.user_id,
                )
            )

        results.sort(key=lambda item: (item.owner_user_id == user_id, item.score), reverse=True)
        return results[:limit]
