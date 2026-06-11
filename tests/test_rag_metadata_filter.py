from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.retrieval_service import retrieve_chunks


def create_user(db, prefix: str = "rag_metadata_filter") -> User:
    suffix = uuid4().hex
    user = User(email=f"{prefix}-{suffix}@example.com", username=f"{prefix}_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_filtered_chunk(
    db,
    *,
    user_id: int,
    knowledge_base: str,
    title: str,
    content: str,
    metadata_json: str,
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base=knowledge_base,
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
        knowledge_base=knowledge_base,
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


def test_position_tag_filter_keeps_matching_chunks() -> None:
    marker = f"position_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "rag_metadata_position")
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="AI app RAG pipeline",
            content=f"{marker} RAG pipeline",
            metadata_json='{"positionTag":"ai_app_intern","category":"technical"}',
        )
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="Python backend API",
            content=f"{marker} RAG pipeline",
            metadata_json='{"positionTag":"python_backend_intern","category":"technical"}',
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query=marker,
            limit=5,
            metadata_filter={"positionTag": "ai_app_intern"},
        )

    assert [hit["title"] for hit in hits] == ["AI app RAG pipeline"]
    assert hits[0]["metadataFilter"] == {"positionTag": "ai_app_intern"}
    assert hits[0]["metadataMatch"] is True


def test_position_tag_filter_excludes_mismatched_chunks() -> None:
    marker = f"exclude_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "rag_metadata_exclude")
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="AI app only",
            content=f"{marker} RAG pipeline",
            metadata_json='{"positionTag":"ai_app_intern","category":"technical"}',
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query=marker,
            limit=5,
            metadata_filter={"positionTag": "python_backend_intern"},
        )

    assert hits == []


def test_category_filter_keeps_matching_chunks() -> None:
    marker = f"category_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "rag_metadata_category")
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="Technical RAG chunk",
            content=f"{marker} retrieval",
            metadata_json='{"positionTag":"ai_app_intern","category":"technical"}',
        )
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="Behavioral RAG chunk",
            content=f"{marker} retrieval",
            metadata_json='{"positionTag":"ai_app_intern","category":"behavioral"}',
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query=marker,
            limit=5,
            metadata_filter={"category": "behavioral"},
        )

    assert [hit["title"] for hit in hits] == ["Behavioral RAG chunk"]


def test_difficulty_filter_works_for_question_bank() -> None:
    marker = f"difficulty_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "rag_metadata_difficulty")
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="question_bank",
            title="Basic RAG question",
            content=f"{marker} explain RAG",
            metadata_json='{"positionTag":"ai_app_intern","category":"technical","difficulty":"basic"}',
        )
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="question_bank",
            title="Hard RAG question",
            content=f"{marker} explain RAG",
            metadata_json='{"positionTag":"ai_app_intern","category":"technical","difficulty":"hard"}',
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="question_bank",
            query=marker,
            limit=5,
            metadata_filter={"difficulty": "hard"},
        )

    assert [hit["title"] for hit in hits] == ["Hard RAG question"]


def test_interview_stage_and_source_filters_work_together() -> None:
    marker = f"stage_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "rag_metadata_stage_source")
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="Project stage manual chunk",
            content=f"{marker} project deep dive",
            metadata_json='{"interviewStage":"project","source":"manual","category":"project"}',
        )
        create_filtered_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="Technical stage imported chunk",
            content=f"{marker} project deep dive",
            metadata_json='{"interviewStage":"technical","source":"imported","category":"project"}',
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query=marker,
            limit=5,
            metadata_filter={"interviewStage": "project", "source": "manual"},
        )

    assert [hit["title"] for hit in hits] == ["Project stage manual chunk"]
