from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.query_rewrite import build_query_variants
from backend_python.rag import retrieve_role_context
from backend_python.retrieval_service import retrieve_multi_query_chunks


def create_user(db, prefix: str = "rag_query_rewrite") -> User:
    suffix = uuid4().hex
    user = User(email=f"{prefix}-{suffix}@example.com", username=f"{prefix}_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_chunk(
    db,
    *,
    user_id: int,
    title: str,
    content: str,
    metadata_json: str = '{"positionTag":"ai_app_intern","category":"technical"}',
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base="role_knowledge",
        source_type="manual",
        content=content,
        metadata_json=metadata_json,
        chunk_count=1,
        status="enabled",
        visibility="private",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    chunk = RagChunk(
        user_id=user_id,
        document_id=document.id,
        knowledge_base="role_knowledge",
        title=title,
        content=content,
        chunk_index=0,
        keywords_json="[]",
        metadata_json=metadata_json,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_build_query_variants_includes_base_role_stage_and_weakness() -> None:
    variants = build_query_variants(
        "RAG log quality",
        profile={
            "targetRole": "AI application intern",
            "positionTag": "ai_app_intern",
            "jd": "RAG retrieval evaluation",
        },
        stage="technical deep dive",
        weakness_tags=["rag_quality"],
    )

    names = [variant["name"] for variant in variants]
    queries = [variant["query"] for variant in variants]

    assert names[:4] == ["base", "role", "stage", "weakness"]
    assert len(queries) == len(set(queries))
    assert "RAG log quality" == queries[0]
    assert any("ai_app_intern" in query for query in queries)
    assert any("technical deep dive" in query for query in queries)
    assert any("rag_quality" in query for query in queries)


def test_retrieve_multi_query_chunks_merges_hits_and_records_variant() -> None:
    marker = f"rewrite_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "rag_query_multi")
        create_chunk(
            db,
            user_id=user.id,
            title="Role variant only chunk",
            content=f"{marker} ai_app_intern retrieval evaluation",
        )

        hits = retrieve_multi_query_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query=marker,
            profile={"positionTag": "ai_app_intern", "targetRole": "AI application intern"},
            stage="technical",
            limit=3,
        )

    assert hits
    assert hits[0]["title"] == "Role variant only chunk"
    assert hits[0]["matchedQueryVariant"] in {"base", "role", "stage"}
    assert [variant["name"] for variant in hits[0]["queryVariants"]][:3] == ["base", "role", "stage"]


def test_role_rag_uses_multi_query_and_returns_variant_metadata() -> None:
    marker = f"role_rewrite_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "rag_query_role")
        create_chunk(
            db,
            user_id=user.id,
            title="Role RAG multi-query chunk",
            content=f"{marker} ai_app_intern query rewrite",
        )

        items = retrieve_role_context(
            {
                "targetRole": "AI application intern",
                "positionTag": "ai_app_intern",
                "resume": marker,
                "jd": "query rewrite",
            },
            "technical",
            db=db,
            user_id=user.id,
        )

    assert items
    assert items[0]["matchedQueryVariant"] in {"base", "role", "stage"}
    assert [variant["name"] for variant in items[0]["queryVariants"]][:3] == ["base", "role", "stage"]
