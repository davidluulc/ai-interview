"""pgvector-backed implementation of the VectorStore Protocol.

Mirror of :class:`backend_python.vector_store.SQLiteVectorStore` for the
PostgreSQL + pgvector deployment: embeddings are double-written to the JSON
columns (SQLite parity) and to ``rag_chunks.embedding_vec`` so the search can
run as SQL cosine-distance instead of an in-memory scan.

Search uses a two-step query in a single statement (stage plan Amendment A):

1. Inner step: approximate nearest neighbours by halfvec cosine distance,
   ordered by ``(embedding_vec::halfvec(2048)) <=> (:q)::halfvec(2048)`` —
   the exact expression of the landed HNSW expression index (pgvector caps
   HNSW ``vector`` indexes at 2000 dimensions, hence the halfvec cast).
2. Outer step: exact full-precision cosine rescore
   (``1 - (embedding_vec <=> (:q)::vector)``) over the recalled candidates.

Documented behaviour difference vs SQLiteVectorStore: results are ordered
purely by SQL cosine distance. There is no "own documents first" Python-side
reordering; scores keep the same semantics (cosine similarity rounded to 4
decimals, non-positive scores skipped).

The SQLAlchemy model deliberately has no ``embedding_vec`` attribute (no
pgvector python dependency); every access goes through raw ``text()`` SQL.
"""

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import DATABASE_URL
from .rag_store import chunk_matches_metadata_filter, dump_json, parse_json
from .vector_store import VectorSearchResult

# Must match alembic/versions/20260909_0001_add_rag_chunks_embedding_vec.py
# and the HNSW expression index defined there.
PG_VECTOR_DIMENSIONS = 2048

# Inner recall multiplier for the approximate step before exact rescoring.
SEARCH_RECALL_MULTIPLIER = 3
SEARCH_MIN_RECALL = 12


def build_pg_dsn() -> str:
    """Return the PostgreSQL DSN to use (TEST_DATABASE_URL overrides DATABASE_URL)."""
    return str(os.getenv("TEST_DATABASE_URL") or DATABASE_URL)


def embedding_literal(values: list[float]) -> str:
    """Render a vector as pgvector literal text, e.g. ``'[0.1,0.2]'``."""
    return "[" + ",".join(repr(float(value)) for value in values) + "]"


class PgVectorStore:
    def __init__(self, db: Session):
        self.db = db

    def upsert_embedding(self, *, chunk_id: int, embedding: list[float], model: str) -> None:
        # Double-write: embedding_vec powers SQL search, the JSON columns keep
        # parity with SQLiteVectorStore (status/model are read by both paths).
        # Note: text() does not parse ":param::type" as a bind (a bind followed
        # by ":" is a literal double-colon), so casts on binds use CAST(...).
        self.db.execute(
            text(
                "UPDATE rag_chunks "
                "SET embedding_vec = CAST(:vec AS vector), "
                "embedding_json = :embedding_json, "
                "embedding_model = :model, "
                "embedding_status = :status "
                "WHERE id = :chunk_id"
            ),
            {
                "vec": embedding_literal(embedding) if embedding else None,
                "embedding_json": dump_json(embedding),
                "model": model,
                "status": "ready" if embedding else "empty",
                "chunk_id": chunk_id,
            },
        )
        self.db.commit()

    def search(
        self,
        *,
        user_id: int,
        knowledge_base: str,
        query_embedding: list[float],
        embedding_model: str | None = None,
        limit: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        if not query_embedding:
            return []
        recall = max(limit * SEARCH_RECALL_MULTIPLIER, SEARCH_MIN_RECALL)
        conditions = [
            "rag_chunks.knowledge_base = :knowledge_base",
            "rag_chunks.embedding_status = 'ready'",
            # <=> yields NULL for NULL vectors and Postgres sorts NULLs first
            # under DESC, so NULL rows must never reach the outer rescore.
            "rag_chunks.embedding_vec IS NOT NULL",
            "rag_documents.status = 'enabled'",
            "(rag_documents.user_id = :user_id OR rag_documents.visibility = 'public')",
        ]
        params: dict[str, Any] = {
            "q": embedding_literal(query_embedding),
            "user_id": user_id,
            "knowledge_base": knowledge_base,
            "recall": recall,
            "limit": limit,
        }
        if embedding_model:
            conditions.append("rag_chunks.embedding_model = :embedding_model")
            params["embedding_model"] = embedding_model
        statement = text(
            f"""
            SELECT rag_chunks.id AS chunk_id,
                   rag_chunks.document_id AS document_id,
                   rag_chunks.knowledge_base AS knowledge_base,
                   rag_chunks.title AS title,
                   rag_chunks.content AS content,
                   rag_chunks.metadata_json AS metadata_json,
                   rag_chunks.embedding_model AS embedding_model,
                   rag_documents.status AS document_status,
                   rag_documents.visibility AS document_visibility,
                   rag_documents.user_id AS owner_user_id,
                   1 - (rag_chunks.embedding_vec <=> CAST(:q AS vector)) AS score
            FROM (
                SELECT rag_chunks.id
                FROM rag_chunks
                JOIN rag_documents ON rag_chunks.document_id = rag_documents.id
                WHERE {" AND ".join(conditions)}
                ORDER BY (rag_chunks.embedding_vec::halfvec({PG_VECTOR_DIMENSIONS}))
                         <=> CAST(:q AS halfvec({PG_VECTOR_DIMENSIONS}))
                LIMIT :recall
            ) candidates
            JOIN rag_chunks ON candidates.id = rag_chunks.id
            JOIN rag_documents ON rag_chunks.document_id = rag_documents.id
            ORDER BY score DESC
            LIMIT :limit
            """
        )
        rows = self.db.execute(statement, params).mappings().all()

        results: list[VectorSearchResult] = []
        for row in rows:
            metadata = parse_json(row["metadata_json"], {})
            if not chunk_matches_metadata_filter(metadata, metadata_filter):
                continue
            score = round(float(row["score"]), 4)
            if score <= 0:
                continue
            results.append(
                VectorSearchResult(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    knowledge_base=row["knowledge_base"],
                    title=row["title"],
                    content=row["content"],
                    score=score,
                    metadata=metadata,
                    embedding_model=row["embedding_model"],
                    document_status=row["document_status"],
                    document_visibility=row["document_visibility"],
                    owner_user_id=row["owner_user_id"],
                )
            )
        return results
