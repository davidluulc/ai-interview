from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.retrieval_service import merge_hybrid_hits, normalize_scores
from backend_python.retrieval_service import retrieve_chunks


def create_hybrid_user(db) -> User:
    suffix = uuid4().hex
    user = User(email=f"hybrid-{suffix}@example.com", username=f"hybrid_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_hybrid_chunk(
    db,
    *,
    user_id: int,
    title: str,
    content: str,
    keywords_json: str,
    embedding_json: str,
) -> RagChunk:
    document = RagDocument(
        user_id=user_id,
        title=title,
        knowledge_base="role_knowledge",
        source_type="manual",
        content=content,
        metadata_json='{"category":"technical"}',
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
        content=content,
        chunk_index=0,
        keywords_json=keywords_json,
        metadata_json=document.metadata_json,
        embedding_json=embedding_json,
        embedding_model="text-embedding-v4",
        embedding_status="ready",
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def test_normalize_scores_maps_values_to_zero_one_range() -> None:
    assert normalize_scores([2.0, 4.0, 6.0]) == [0.0, 0.5, 1.0]


def test_normalize_scores_gives_single_positive_score_full_weight() -> None:
    assert normalize_scores([3.5]) == [1.0]


def test_normalize_scores_handles_empty_and_flat_scores() -> None:
    assert normalize_scores([]) == []
    assert normalize_scores([0.0, 0.0]) == [0.0, 0.0]
    assert normalize_scores([2.0, 2.0]) == [1.0, 1.0]


def test_merge_hybrid_hits_deduplicates_by_chunk_id_and_records_modes() -> None:
    bm25_hits = [
        {
            "retrievalMode": "bm25",
            "chunkId": 1,
            "documentId": 10,
            "title": "RAG 日志",
            "content": "记录 query_text 和 hit_count",
            "score": 3.0,
            "matchedTokens": ["rag"],
            "matchedKeywords": ["RAG"],
            "metadata": {"category": "technical"},
        }
    ]
    vector_hits = [
        {
            "retrievalMode": "vector",
            "chunkId": 1,
            "documentId": 10,
            "title": "RAG 日志",
            "content": "记录 query_text 和 hit_count",
            "score": 0.8,
            "matchedTokens": [],
            "matchedKeywords": [],
            "metadata": {"category": "technical"},
            "embeddingStatus": "ready",
        }
    ]

    merged = merge_hybrid_hits(bm25_hits, vector_hits, limit=3)

    assert len(merged) == 1
    assert merged[0]["retrievalMode"] == "hybrid"
    assert merged[0]["matchedRetrievalModes"] == ["bm25", "vector"]
    assert merged[0]["bm25Score"] == 3.0
    assert merged[0]["vectorScore"] == 0.8
    assert merged[0]["score"] == merged[0]["hybridScore"]


def test_retrieve_chunks_hybrid_combines_bm25_and_vector(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_hybrid_user(db)
        create_hybrid_chunk(
            db,
            user_id=user.id,
            title="RAG 日志工程化",
            content="RAG 日志记录 query_text、retriever_name、hit_count、quality。",
            keywords_json='["RAG", "quality"]',
            embedding_json="[0.95, 0.05, 0.0]",
        )
        create_hybrid_chunk(
            db,
            user_id=user.id,
            title="FastAPI 模块化",
            content="FastAPI 使用 APIRouter 拆分后端模块。",
            keywords_json='["FastAPI", "APIRouter"]',
            embedding_json="[0.1, 0.8, 0.0]",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="RAG quality 命中日志",
            limit=3,
            mode="hybrid",
        )

    assert hits
    assert hits[0]["retrievalMode"] == "hybrid"
    assert "bm25" in hits[0]["matchedRetrievalModes"]
    assert "vector" in hits[0]["matchedRetrievalModes"]
    assert hits[0]["title"] == "RAG 日志工程化"


def test_retrieve_chunks_hybrid_falls_back_to_bm25_when_vector_fails(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        raise RuntimeError("embedding provider failed")

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_hybrid_user(db)
        create_hybrid_chunk(
            db,
            user_id=user.id,
            title="RAG 日志工程化",
            content="RAG 日志记录 query_text 和 quality。",
            keywords_json='["RAG", "quality"]',
            embedding_json="[0.95, 0.05, 0.0]",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="RAG quality",
            limit=3,
            mode="hybrid",
        )

    assert hits
    assert hits[0]["retrievalMode"] == "hybrid"
    assert hits[0]["matchedRetrievalModes"] == ["bm25"]
    assert hits[0]["vectorScore"] == 0.0
