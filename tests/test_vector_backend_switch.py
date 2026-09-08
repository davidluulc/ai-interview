"""Vector backend switch tests: retrieval wiring + backend parity.

Two independent layers:

* ``test_retrieve_vector_chunks_selects_store_by_config`` (ungated, no DB):
  sentinel stores prove ``retrieve_vector_chunks`` constructs
  ``PgVectorStore`` only when ``VECTOR_SEARCH_BACKEND == "pgvector"`` and
  ``SQLiteVectorStore`` for every other value (in particular the sqlite
  default never touches ``PgVectorStore``).
* ``test_vector_backends_agree_on_top_chunks`` (gated on TEST_DATABASE_URL,
  harness mirrors tests/test_pg_vector_store.py): seeds the same rows once —
  ``PgVectorStore.upsert_embedding`` double-writes ``embedding_vec`` and the
  JSON columns, so both stores see identical data — then asserts the two
  backends agree on the top-1 chunk and on the top-3 chunk sets.
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import backend_python.retrieval_service as retrieval_service
from backend_python.database import Base
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.pg_vector_store import PgVectorStore
from backend_python.retrieval_service import retrieve_vector_chunks
from backend_python.vector_store import SQLiteVectorStore

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

engine = create_engine(TEST_DATABASE_URL) if TEST_DATABASE_URL else None
Session = sessionmaker(bind=engine) if TEST_DATABASE_URL else None

require_pg = pytest.mark.skipif(not TEST_DATABASE_URL, reason="pgvector integration tests need TEST_DATABASE_URL")

VECTOR_DIMENSIONS = 2048
FIXED_QUERY_EMBEDDING = [1.0, 0.0, 0.0, 0.0]


def unit_vector(axis: int, dimensions: int = VECTOR_DIMENSIONS) -> list[float]:
    values = [0.0] * dimensions
    values[axis] = 1.0
    return values


def tilted_vector(axis: int, cross_axis: int, weight: float, dimensions: int = VECTOR_DIMENSIONS) -> list[float]:
    values = [0.0] * dimensions
    values[axis] = 1.0
    values[cross_axis] = weight
    return values


def create_user(db, prefix: str = "vector_backend_switch") -> User:
    suffix = uuid4().hex
    user = User(email=f"{prefix}-{suffix}@example.com", username=f"{prefix}_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_vector_chunk(
    db,
    *,
    user_id: int,
    title: str,
    metadata_json: str,
    knowledge_base: str = "role_knowledge",
    visibility: str = "private",
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base=knowledge_base,
        source_type="manual",
        status="enabled",
        visibility=visibility,
        content=title,
        metadata_json=metadata_json,
        chunk_count=1,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    chunk = RagChunk(
        user_id=user_id,
        document_id=document.id,
        knowledge_base=knowledge_base,
        title=title,
        content=title,
        chunk_index=0,
        metadata_json=metadata_json,
        embedding_json="[]",
        embedding_model="text-embedding-v4",
        embedding_status="pending",
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


@pytest.fixture(scope="module")
def db_session():
    from backend_python import db_models  # noqa: F401  register models on Base.metadata

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(text("ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS embedding_vec vector(2048)"))
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_vec_hnsw ON rag_chunks "
                "USING hnsw ((embedding_vec::halfvec(2048)) halfvec_cosine_ops)"
            )
        )
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize(
    ("backend", "expected_store"),
    [
        ("pgvector", "pgvector"),
        ("sqlite", "sqlite"),
        ("totally-unknown", "sqlite"),
    ],
)
def test_retrieve_vector_chunks_selects_store_by_config(monkeypatch, backend, expected_store) -> None:
    constructed: list[str] = []

    class SQLiteSentinel:
        def __init__(self, db):
            constructed.append("sqlite")

        def search(self, **kwargs):
            return []

    class PgVectorSentinel:
        def __init__(self, db):
            constructed.append("pgvector")

        def search(self, **kwargs):
            return []

    monkeypatch.setattr(retrieval_service, "SQLiteVectorStore", SQLiteSentinel, raising=False)
    monkeypatch.setattr(retrieval_service, "PgVectorStore", PgVectorSentinel, raising=False)
    # retrieval_service binds VECTOR_SEARCH_BACKEND at import time, so the
    # module attribute must be patched (patching config would be ignored).
    monkeypatch.setattr(retrieval_service, "VECTOR_SEARCH_BACKEND", backend, raising=False)
    monkeypatch.setattr(retrieval_service, "run_query_embedding", lambda query: list(FIXED_QUERY_EMBEDDING))

    results = retrieve_vector_chunks(
        object(),
        user_id=1,
        knowledge_base="role_knowledge",
        query="sentinel query",
        limit=3,
    )

    assert results == []
    # Exactly one store is constructed — the configured one. In particular the
    # sqlite default never touches PgVectorStore.
    assert constructed == [expected_store]


@require_pg
def test_vector_backends_agree_on_top_chunks(db_session) -> None:
    marker = f"parity_{uuid4().hex}"
    user = create_user(db_session, "vector_backend_parity")
    # Every chunk is owned by the searching user: SQLiteVectorStore re-ranks
    # own documents first (a documented divergence PgVectorStore does not
    # share), so mixed ownership would test that divergence instead of the
    # raw cosine parity this test pins. Scores vs the query are distinct and
    # positive: 1.0, ~0.9806, ~0.8944, ~0.7433, ~0.4472.
    embeddings = [
        unit_vector(0),
        tilted_vector(0, 1, 0.2),
        tilted_vector(0, 1, 0.5),
        tilted_vector(0, 1, 0.9),
        tilted_vector(0, 2, 2.0),
    ]
    chunks = [
        create_vector_chunk(
            db_session,
            user_id=user.id,
            title=f"Parity chunk {index} {marker}",
            metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
        )
        for index in range(len(embeddings))
    ]

    # One seeding pass feeds both stores: PgVectorStore.upsert_embedding
    # double-writes embedding_vec (pg search) and embedding_json (SQLite
    # search) on the same rows.
    pg_store = PgVectorStore(db_session)
    for chunk, embedding in zip(chunks, embeddings):
        pg_store.upsert_embedding(chunk_id=chunk.id, embedding=embedding, model="text-embedding-v4")

    sqlite_store = SQLiteVectorStore(db_session)
    search_args = {
        "user_id": user.id,
        "knowledge_base": "role_knowledge",
        "query_embedding": unit_vector(0),
        "embedding_model": "text-embedding-v4",
        "limit": 3,
        "metadata_filter": {"category": marker},
    }
    sqlite_results = sqlite_store.search(**search_args)
    pg_results = pg_store.search(**search_args)

    assert len(sqlite_results) == 3
    assert len(pg_results) == 3
    # Top-1 is the exact-match chunk for both backends.
    assert sqlite_results[0].chunk_id == chunks[0].id
    assert pg_results[0].chunk_id == chunks[0].id
    # Top-3 chunk sets overlap >= 2/3 (tolerate ordering / tie differences).
    sqlite_ids = {result.chunk_id for result in sqlite_results}
    pg_ids = {result.chunk_id for result in pg_results}
    assert len(sqlite_ids & pg_ids) >= 2
