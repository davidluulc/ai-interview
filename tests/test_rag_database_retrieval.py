from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.question_rag import retrieve_questions
from backend_python.rag import retrieve_role_context


def create_user(db, prefix: str = "rag_retrieval") -> User:
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
    knowledge_base: str,
    title: str,
    content: str,
    metadata_json: str = "{}",
    keywords_json: str = "[]",
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base=knowledge_base,
        source_type="manual",
        content=content,
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
        content=content,
        chunk_index=0,
        keywords_json=keywords_json,
        metadata_json=metadata_json,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_role_rag_retrieves_user_database_chunk_first() -> None:
    with SessionLocal() as db:
        user = create_user(db, "role_chunk")
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="FastAPI RAG 项目追问",
            content="候选人做过 FastAPI RAG 系统时，需要追问文档切片、召回日志和权限隔离。",
            keywords_json='["FastAPI", "RAG", "权限隔离"]',
        )

        items = retrieve_role_context(
            {
                "targetRole": "AI 应用开发实习生",
                "resume": "FastAPI RAG 模拟面试系统",
                "jd": "要求理解 RAG 权限隔离和召回日志",
            },
            "技术追问",
            db=db,
            user_id=user.id,
        )

    assert items
    assert items[0]["source"] == "database"
    assert items[0]["retrievalMode"] == "bm25"
    assert items[0]["chunkId"] == chunk_id_or_any(items[0]["chunkId"])
    assert "权限隔离" in items[0]["content"]


def test_question_rag_retrieves_user_database_chunk_first() -> None:
    with SessionLocal() as db:
        user = create_user(db, "question_chunk")
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="question_bank",
            title="RAG 日志追问题",
            content="请说明你的 RAG 命中日志记录了哪些字段，以及如何用它判断召回质量。",
            metadata_json='{"positionTag": "ai_app_intern", "category": "technical", "difficulty": "medium"}',
            keywords_json='["RAG", "命中日志", "召回质量"]',
        )

        questions = retrieve_questions(
            {
                "targetRole": "AI 应用开发实习生",
                "positionTag": "ai_app_intern",
                "resume": "做过 RAG 命中日志",
                "jd": "需要理解召回质量",
            },
            "技术追问",
            db=db,
            user_id=user.id,
        )

    assert questions
    assert questions[0]["source"] == "database"
    assert questions[0]["retrievalMode"] == "bm25"
    assert questions[0]["question"].startswith("请说明你的 RAG 命中日志")
    assert questions[0]["position_tag"] == "ai_app_intern"


def test_role_rag_applies_profile_position_tag_metadata_filter() -> None:
    marker = f"role_filter_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "role_filter")
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="AI app filtered role knowledge",
            content=f"{marker} explain RAG metadata filter for AI app",
            metadata_json='{"positionTag": "ai_app_intern", "category": "technical"}',
        )
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="Python backend filtered role knowledge",
            content=f"{marker} explain RAG metadata filter for backend",
            metadata_json='{"positionTag": "python_backend_intern", "category": "technical"}',
        )

        items = retrieve_role_context(
            {
                "targetRole": "AI app intern",
                "positionTag": "ai_app_intern",
                "resume": marker,
                "jd": "metadata filter",
            },
            "technical",
            db=db,
            user_id=user.id,
        )

    assert items
    assert items[0]["title"] == "AI app filtered role knowledge"
    assert items[0]["metadataFilter"] == {"positionTag": "ai_app_intern"}
    assert items[0]["metadataMatch"] is True


def test_question_rag_applies_profile_position_tag_metadata_filter() -> None:
    marker = f"question_filter_{uuid4().hex}"
    with SessionLocal() as db:
        user = create_user(db, "question_filter")
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="question_bank",
            title="AI app filtered question",
            content=f"{marker} explain RAG metadata filter for AI app",
            metadata_json='{"positionTag": "ai_app_intern", "category": "technical", "difficulty": "medium"}',
        )
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="question_bank",
            title="Python backend filtered question",
            content=f"{marker} explain RAG metadata filter for backend",
            metadata_json='{"positionTag": "python_backend_intern", "category": "technical", "difficulty": "medium"}',
        )

        questions = retrieve_questions(
            {
                "targetRole": "AI app intern",
                "positionTag": "ai_app_intern",
                "resume": marker,
                "jd": "metadata filter",
            },
            "technical",
            db=db,
            user_id=user.id,
        )

    assert questions
    assert questions[0]["question"].startswith(f"{marker} explain RAG metadata filter for AI app")
    assert questions[0]["metadataFilter"] == {"positionTag": "ai_app_intern"}
    assert questions[0]["metadataMatch"] is True


def test_role_rag_keeps_seed_fallback_without_database_match() -> None:
    items = retrieve_role_context(
        {
            "targetRole": "AI 应用开发实习生",
            "resume": "FastAPI Qwen RAG 模拟面试系统",
            "jd": "大模型 API RAG Agent Python 后端",
        },
        "技术追问",
    )

    assert items
    assert items[0]["score"] > 0


def chunk_id_or_any(value: int) -> int:
    assert isinstance(value, int)
    return value
