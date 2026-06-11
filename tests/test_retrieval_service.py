from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.retrieval_service import bm25_score, retrieve_chunks, tokenize


def create_user(db, prefix: str = "retrieval_service") -> User:
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
    keywords_json: str = "[]",
    metadata_json: str = "{}",
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


def test_tokenize_keeps_chinese_terms_and_technical_words() -> None:
    assert tokenize("FastAPI RAG 命中日志 qwen3-rerank") == ["fastapi", "rag", "命中日志", "qwen3-rerank"]


def test_bm25_score_prefers_matching_document() -> None:
    query_tokens = tokenize("RAG 命中日志")
    documents = [
        tokenize("RAG 命中日志 召回质量"),
        tokenize("FastAPI 路由 SQLAlchemy"),
    ]

    matching_score = bm25_score(query_tokens, documents[0], documents)
    unrelated_score = bm25_score(query_tokens, documents[1], documents)

    assert matching_score > unrelated_score
    assert matching_score > 0


def test_retrieve_chunks_returns_bm25_database_hits() -> None:
    with SessionLocal() as db:
        user = create_user(db)
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="RAG 日志工程化",
            content="RAG 命中日志需要记录 query、retriever、hit_count 和 quality。",
            keywords_json='["RAG", "命中日志", "quality"]',
        )
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            title="FastAPI 路由拆分",
            content="FastAPI 项目可以用 APIRouter 拆分路由。",
            keywords_json='["FastAPI", "APIRouter"]',
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="请追问 RAG 命中日志 quality 字段",
            limit=2,
        )

    assert hits
    assert hits[0]["retrievalMode"] == "bm25"
    assert hits[0]["source"] == "database"
    assert "rag" in hits[0]["matchedTokens"] or "命中日志" in hits[0]["matchedTokens"]
    assert hits[0]["score"] > 0
    assert hits[0]["title"] == "RAG 日志工程化"


def test_retrieve_chunks_supports_candidate_memory_knowledge_base() -> None:
    with SessionLocal() as db:
        user = create_user(db, prefix="candidate_memory_retrieval")
        create_chunk(
            db,
            user_id=user.id,
            knowledge_base="candidate_memory",
            title="候选人 RAG 薄弱点",
            content="候选人历史回答中多次无法说明 RAG query 构造、chunk 切分和召回质量。",
            keywords_json='["候选人", "RAG", "query", "chunk", "召回质量"]',
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="candidate_memory",
            query="候选人 RAG query chunk 召回质量",
            limit=2,
        )

    assert hits
    assert hits[0]["knowledgeBase"] == "candidate_memory"
    assert hits[0]["title"] == "候选人 RAG 薄弱点"
