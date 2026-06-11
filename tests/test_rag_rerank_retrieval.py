from uuid import uuid4

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.retrieval_service import apply_rerank_results, hit_to_rerank_document
from backend_python.retrieval_service import retrieve_chunks


def create_rerank_user(db) -> User:
    suffix = uuid4().hex
    user = User(email=f"rerank-{suffix}@example.com", username=f"rerank_{suffix[:10]}", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_rerank_chunk(
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


def test_hit_to_rerank_document_includes_title_content_and_metadata() -> None:
    text = hit_to_rerank_document(
        {
            "title": "RAG 日志工程化",
            "content": "记录 query_text 和 hit_count。",
            "metadata": {"category": "technical"},
        }
    )

    assert "标题：RAG 日志工程化" in text
    assert "内容：记录 query_text 和 hit_count。" in text
    assert "technical" in text


def test_apply_rerank_results_reorders_hits_and_records_debug_fields() -> None:
    hits = [
        {"chunkId": 1, "title": "A", "score": 0.5, "matchedRetrievalModes": ["bm25"], "hybridScore": 0.5},
        {"chunkId": 2, "title": "B", "score": 0.7, "matchedRetrievalModes": ["vector"], "hybridScore": 0.7},
    ]
    reranked = apply_rerank_results(
        hits,
        [
            {"index": 1, "relevance_score": 0.93},
            {"index": 0, "relevance_score": 0.61},
        ],
        limit=2,
    )

    assert [hit["chunkId"] for hit in reranked] == [2, 1]
    assert reranked[0]["retrievalMode"] == "hybrid_rerank"
    assert reranked[0]["score"] == 0.93
    assert reranked[0]["rerankScore"] == 0.93
    assert reranked[0]["rerankIndex"] == 1
    assert reranked[0]["preRerankRank"] == 2
    assert "rerank" in reranked[0]["matchedRetrievalModes"]


def test_retrieve_chunks_hybrid_rerank_reorders_hybrid_candidates(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    async def fake_rerank_documents(query: str, documents: list[str], top_n: int) -> list[dict]:
        return [
            {"index": 1, "relevance_score": 0.96},
            {"index": 0, "relevance_score": 0.63},
        ]

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)
    monkeypatch.setattr("backend_python.retrieval_service.rerank_documents", fake_rerank_documents)

    with SessionLocal() as db:
        user = create_rerank_user(db)
        create_rerank_chunk(
            db,
            user_id=user.id,
            title="RAG 日志工程化",
            content="RAG 日志记录 query_text 和 quality。",
            keywords_json='["RAG", "quality"]',
            embedding_json="[0.95, 0.05, 0.0]",
        )
        create_rerank_chunk(
            db,
            user_id=user.id,
            title="面试追问策略",
            content="面试官应该围绕候选人回答继续追问。",
            keywords_json='["面试", "追问"]',
            embedding_json="[0.7, 0.2, 0.0]",
        )

        hits = retrieve_chunks(
            db,
            user_id=user.id,
            knowledge_base="role_knowledge",
            query="RAG 面试追问",
            limit=2,
            mode="hybrid_rerank",
        )

    assert hits[0]["retrievalMode"] == "hybrid_rerank"
    assert hits[0]["rerankScore"] == 0.96
    assert "rerank" in hits[0]["matchedRetrievalModes"]


def test_retrieve_chunks_hybrid_rerank_falls_back_to_hybrid_when_rerank_fails(monkeypatch) -> None:
    async def fake_embed_text(text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    async def fake_rerank_documents(query: str, documents: list[str], top_n: int) -> list[dict]:
        raise RuntimeError("rerank provider failed")

    monkeypatch.setattr("backend_python.retrieval_service.embed_text", fake_embed_text)
    monkeypatch.setattr("backend_python.retrieval_service.rerank_documents", fake_rerank_documents)

    with SessionLocal() as db:
        user = create_rerank_user(db)
        create_rerank_chunk(
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
            limit=2,
            mode="hybrid_rerank",
        )

    assert hits
    assert hits[0]["retrievalMode"] == "hybrid"
    assert "rerankScore" not in hits[0]
