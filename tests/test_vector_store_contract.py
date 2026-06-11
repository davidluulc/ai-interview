from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.vector_store import SQLiteVectorStore, cosine_similarity, parse_embedding


def create_user(db, prefix: str = "vector_store") -> User:
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
    embedding_json: str = "[]",
    embedding_status: str = "ready",
    metadata_json: str = '{"positionTag":"ai_app_intern","category":"technical"}',
    status: str = "enabled",
    visibility: str = "private",
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base="role_knowledge",
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
        knowledge_base="role_knowledge",
        title=title,
        content=title,
        chunk_index=0,
        metadata_json=metadata_json,
        embedding_json=embedding_json,
        embedding_model="text-embedding-v4",
        embedding_status=embedding_status,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_parse_embedding_and_cosine_similarity_are_stable() -> None:
    assert parse_embedding("[1, 0, 0]") == [1.0, 0.0, 0.0]
    assert parse_embedding("not-json") == []
    assert cosine_similarity([1, 0], [1, 0]) == 1.0
    assert cosine_similarity([1, 0], [0, 1]) == 0.0


def test_sqlite_vector_store_upserts_embedding_and_searches_by_similarity() -> None:
    marker = f"upsert_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "vector_store_upsert")
        chunk = create_vector_chunk(
            db,
            user_id=user.id,
            title=f"RAG vector store {marker}",
            embedding_json="[]",
            embedding_status="pending",
            metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
        )
        store = SQLiteVectorStore(db)

        store.upsert_embedding(chunk_id=chunk.id, embedding=[0.0, 0.0, 1.0], model="text-embedding-v4")
        results = store.search(
            user_id=user.id,
            knowledge_base="role_knowledge",
            query_embedding=[0.0, 0.0, 1.0],
            limit=3,
            metadata_filter={"category": marker},
        )

    assert [result.title for result in results] == [f"RAG vector store {marker}"]
    assert results[0].score == 1.0
    assert results[0].embedding_model == "text-embedding-v4"


def test_sqlite_vector_store_respects_visibility_status_and_metadata_filter() -> None:
    marker = f"visibility_{uuid4().hex}"
    with SessionLocal() as db:
        owner = create_user(db, "vector_store_owner")
        reader = create_user(db, "vector_store_reader")
        create_vector_chunk(
            db,
            user_id=owner.id,
            title=f"Public AI app vector chunk {marker}",
            embedding_json="[0, 0, 1]",
            visibility="public",
            metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
        )
        create_vector_chunk(
            db,
            user_id=owner.id,
            title=f"Private AI app vector chunk {marker}",
            embedding_json="[0, 0, 1]",
            visibility="private",
            metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
        )
        create_vector_chunk(
            db,
            user_id=owner.id,
            title=f"Disabled AI app vector chunk {marker}",
            embedding_json="[0, 0, 1]",
            status="disabled",
            visibility="public",
            metadata_json=f'{{"positionTag":"ai_app_intern","category":"{marker}"}}',
        )
        create_vector_chunk(
            db,
            user_id=owner.id,
            title=f"Public Python vector chunk {marker}",
            embedding_json="[0, 0, 1]",
            visibility="public",
            metadata_json=f'{{"positionTag":"python_backend_intern","category":"{marker}"}}',
        )
        store = SQLiteVectorStore(db)

        results = store.search(
            user_id=reader.id,
            knowledge_base="role_knowledge",
            query_embedding=[0.0, 0.0, 1.0],
            limit=5,
            metadata_filter={"positionTag": "ai_app_intern", "category": marker},
        )

    assert [result.title for result in results] == [f"Public AI app vector chunk {marker}"]
