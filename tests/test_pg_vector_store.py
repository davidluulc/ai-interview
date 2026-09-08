"""Integration tests for the pgvector-backed PgVectorStore.

The whole module is gated on TEST_DATABASE_URL so the default suite stays
green without a running pgvector container. Per the stage plan amendment the
module builds its own engine (never SessionLocal, which is bound to the
app DATABASE_URL) and creates the schema it needs via Base.metadata plus the
migration's embedding_vec column and HNSW expression index.
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend_python.database import Base
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.pg_vector_store import PgVectorStore, embedding_literal
from backend_python.vector_store import cosine_similarity, parse_embedding

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="pgvector integration tests need TEST_DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL) if TEST_DATABASE_URL else None
Session = sessionmaker(bind=engine) if TEST_DATABASE_URL else None

VECTOR_DIMENSIONS = 2048


def unit_vector(axis: int, dimensions: int = VECTOR_DIMENSIONS) -> list[float]:
    values = [0.0] * dimensions
    values[axis] = 1.0
    return values


def tilted_vector(axis: int, cross_axis: int, weight: float, dimensions: int = VECTOR_DIMENSIONS) -> list[float]:
    values = [0.0] * dimensions
    values[axis] = 1.0
    values[cross_axis] = weight
    return values


def create_user(db, prefix: str = "pg_vector_store") -> User:
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
    embedding_json: str = "[]",
    embedding_model: str = "text-embedding-v4",
    embedding_status: str = "pending",
    status: str = "enabled",
    visibility: str = "private",
    knowledge_base: str = "role_knowledge",
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base=knowledge_base,
        source_type="manual",
        status=status,
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
        embedding_json=embedding_json,
        embedding_model=embedding_model,
        embedding_status=embedding_status,
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
        # Mirror the landed migration's HNSW expression index so the two-step
        # search SQL is exercised against the real index expression.
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


def test_pg_vector_store_upserts_embedding_and_searches_by_distance(db_session) -> None:
    marker = f"upsert_{uuid4().hex}"
    user = create_user(db_session, "pg_vector_store_upsert")
    near = create_vector_chunk(
        db_session,
        user_id=user.id,
        title=f"PG near vector chunk {marker}",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
    )
    mid = create_vector_chunk(
        db_session,
        user_id=user.id,
        title=f"PG mid vector chunk {marker}",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
    )
    far = create_vector_chunk(
        db_session,
        user_id=user.id,
        title=f"PG far vector chunk {marker}",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
    )
    store = PgVectorStore(db_session)

    near_vec = tilted_vector(0, 1, 0.01)
    mid_vec = tilted_vector(0, 1, 0.5)
    far_vec = unit_vector(2)
    assert embedding_literal([0.1, 0.2]) == "[0.1,0.2]"

    store.upsert_embedding(chunk_id=near.id, embedding=near_vec, model="text-embedding-v4")
    store.upsert_embedding(chunk_id=mid.id, embedding=mid_vec, model="text-embedding-v4")
    store.upsert_embedding(chunk_id=far.id, embedding=far_vec, model="text-embedding-v4")

    refreshed = db_session.get(RagChunk, near.id)
    assert refreshed is not None
    assert refreshed.embedding_status == "ready"
    assert refreshed.embedding_model == "text-embedding-v4"
    assert parse_embedding(refreshed.embedding_json) == near_vec

    results = store.search(
        user_id=user.id,
        knowledge_base="role_knowledge",
        query_embedding=near_vec,
        limit=5,
        metadata_filter={"category": marker},
    )

    assert [result.title for result in results] == [
        f"PG near vector chunk {marker}",
        f"PG mid vector chunk {marker}",
    ]
    assert results[0].score == 1.0
    assert results[1].score == cosine_similarity(near_vec, mid_vec)
    assert results[0].embedding_model == "text-embedding-v4"

    # The optional embedding_model WHERE branch excludes non-matching models.
    assert (
        store.search(
            user_id=user.id,
            knowledge_base="role_knowledge",
            query_embedding=near_vec,
            embedding_model="other-model",
            limit=5,
            metadata_filter={"category": marker},
        )
        == []
    )


def test_pg_vector_store_applies_metadata_filter(db_session) -> None:
    marker = f"filter_{uuid4().hex}"
    user = create_user(db_session, "pg_vector_store_filter")
    matching = create_vector_chunk(
        db_session,
        user_id=user.id,
        title=f"PG matching metadata chunk {marker}",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
    )
    other = create_vector_chunk(
        db_session,
        user_id=user.id,
        title=f"PG other metadata chunk {marker}",
        metadata_json=f'{{"positionTag":"python_backend_intern","category":"{marker}"}}',
    )
    store = PgVectorStore(db_session)
    store.upsert_embedding(chunk_id=matching.id, embedding=unit_vector(0), model="text-embedding-v4")
    store.upsert_embedding(chunk_id=other.id, embedding=unit_vector(0), model="text-embedding-v4")

    results = store.search(
        user_id=user.id,
        knowledge_base="role_knowledge",
        query_embedding=unit_vector(0),
        limit=5,
        metadata_filter={"positionTag": "ai_app_intern", "category": marker},
    )

    assert [result.title for result in results] == [f"PG matching metadata chunk {marker}"]


def test_pg_vector_store_owner_public_visibility_matches_sqlite_semantics(db_session) -> None:
    marker = f"visibility_{uuid4().hex}"
    owner = create_user(db_session, "pg_vector_store_owner")
    reader = create_user(db_session, "pg_vector_store_reader")
    public_chunk = create_vector_chunk(
        db_session,
        user_id=owner.id,
        title=f"PG public chunk {marker}",
        visibility="public",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
    )
    private_chunk = create_vector_chunk(
        db_session,
        user_id=owner.id,
        title=f"PG other user private chunk {marker}",
        visibility="private",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
    )
    own_private_chunk = create_vector_chunk(
        db_session,
        user_id=reader.id,
        title=f"PG reader own private chunk {marker}",
        visibility="private",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
    )
    store = PgVectorStore(db_session)
    for chunk in (public_chunk, private_chunk, own_private_chunk):
        store.upsert_embedding(chunk_id=chunk.id, embedding=unit_vector(1), model="text-embedding-v4")

    results = store.search(
        user_id=reader.id,
        knowledge_base="role_knowledge",
        query_embedding=unit_vector(1),
        limit=5,
        metadata_filter={"category": marker},
    )

    assert {result.title for result in results} == {
        f"PG public chunk {marker}",
        f"PG reader own private chunk {marker}",
    }
    for result in results:
        assert result.document_status == "enabled"
        assert result.knowledge_base == "role_knowledge"
        assert result.chunk_id in {public_chunk.id, own_private_chunk.id}


def test_pg_vector_store_ranks_purely_by_score_not_own_documents_first(db_session) -> None:
    marker = f"ordering_{uuid4().hex}"
    owner = create_user(db_session, "pg_vector_store_order_owner")
    reader = create_user(db_session, "pg_vector_store_order_reader")
    # Both scores stay positive (a fully orthogonal "far" vector would score
    # 0.0 and be skipped like in the SQLite store): near ~0.9806, far ~0.4472.
    near_vec = tilted_vector(0, 1, 0.2)
    far_vec = tilted_vector(3, 0, 0.5)
    public_near = create_vector_chunk(
        db_session,
        user_id=owner.id,
        title=f"PG owner public near chunk {marker}",
        visibility="public",
        knowledge_base="ordering_probe",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}_a"}}',
    )
    own_far = create_vector_chunk(
        db_session,
        user_id=reader.id,
        title=f"PG reader own far chunk {marker}",
        visibility="private",
        knowledge_base="ordering_probe",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}_a"}}',
    )
    own_near = create_vector_chunk(
        db_session,
        user_id=reader.id,
        title=f"PG reader own near chunk {marker}",
        visibility="private",
        knowledge_base="ordering_probe",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}_b"}}',
    )
    public_far = create_vector_chunk(
        db_session,
        user_id=owner.id,
        title=f"PG owner public far chunk {marker}",
        visibility="public",
        knowledge_base="ordering_probe",
        metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}_b"}}',
    )
    store = PgVectorStore(db_session)
    for chunk, embedding in (
        (public_near, near_vec),
        (own_far, far_vec),
        (own_near, near_vec),
        (public_far, far_vec),
    ):
        store.upsert_embedding(chunk_id=chunk.id, embedding=embedding, model="text-embedding-v4")

    # Divergence from SQLiteVectorStore: the OTHER user's public chunk outranks
    # the reader's OWN private chunk. The SQLite store's own-documents-first
    # re-rank would flip this pair; PgVectorStore orders purely by score.
    diverged = store.search(
        user_id=reader.id,
        knowledge_base="ordering_probe",
        query_embedding=unit_vector(0),
        limit=5,
        metadata_filter={"category": f"{marker}_a"},
    )
    assert [result.title for result in diverged] == [
        f"PG owner public near chunk {marker}",
        f"PG reader own far chunk {marker}",
    ]
    assert diverged[0].owner_user_id == owner.id
    assert diverged[1].owner_user_id == reader.id

    # Reversed distances: the own chunk wins purely because it scores higher.
    reversed_order = store.search(
        user_id=reader.id,
        knowledge_base="ordering_probe",
        query_embedding=unit_vector(0),
        limit=5,
        metadata_filter={"category": f"{marker}_b"},
    )
    assert [result.title for result in reversed_order] == [
        f"PG reader own near chunk {marker}",
        f"PG owner public far chunk {marker}",
    ]
