from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.retrieval_service import cosine_similarity, retrieve_chunks


def create_user(db, prefix: str = "rag_vector") -> User:
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
    knowledge_base: str,
    title: str,
    content: str,
    embedding_json: str,
    embedding_status: str = "ready",
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base=knowledge_base,
        source_type="manual",
        content=content,
        metadata_json="{}",
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
        keywords_json="[]",
        metadata_json="{}",
        embedding_json=embedding_json,
        embedding_model="text-embedding-v4",
        embedding_status=embedding_status,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_cosine_similarity_prefers_same_direction() -> None:
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == 1.0
    assert cosine_similarity([1, 0, 0], [0, 1, 0]) == 0.0
    assert cosine_similarity([], [1, 0, 0]) == 0.0


def test_retrieve_chunks_vector_mode_orders_by_embedding_similarity(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        assert text == "RAG 命中日志 quality"
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_user(db)
        create_vector_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="RAG 日志质量评估",
            content="讲解 query_text、retriever_name、hit_count 和 quality。",
            embedding_json="[0.95, 0.05, 0.0]",
        )
        create_vector_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="FastAPI 路由拆分",
            content="讲解 APIRouter 和后端模块化。",
            embedding_json="[0.2, 0.9, 0.0]",
        )
        create_vector_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="未完成向量",
            content="这个 chunk 不应该参与向量召回。",
            embedding_json="[1.0, 0.0, 0.0]",
            embedding_status="failed",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="RAG 命中日志 quality",
            limit=2,
            mode="vector",
        )

    assert [hit["title"] for hit in hits] == ["RAG 日志质量评估", "FastAPI 路由拆分"]
    assert hits[0]["retrievalMode"] == "vector"
    assert hits[0]["embeddingStatus"] == "ready"
    assert hits[0]["score"] > hits[1]["score"]


def test_retrieve_chunks_vector_mode_returns_empty_when_query_embedding_fails(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        raise RuntimeError("embedding failed")

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_user(db, prefix="rag_vector_fail")
        create_vector_chunk(
            db,
            user_id=user.id,
            knowledge_base="question_bank",
            title="RAG 题目",
            content="什么是 RAG 召回？",
            embedding_json="[1.0, 0.0, 0.0]",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="question_bank",
            query="RAG 召回",
            mode="vector",
        )

    assert hits == []
