import pytest

from backend_python import retrieval_service
from backend_python.retrieval_service import rrf_fuse, retrieve_hybrid_chunks


def install_hybrid_fetchers(monkeypatch: pytest.MonkeyPatch) -> None:
    """让 retrieve_hybrid_chunks 的两路召回返回固定命中，隔离 DB 与 embedding。

    bm25 路与 vector 路共同命中 chunk 12（bm25 rank2 + vector rank1）：rrf 下它以
    1/62 + 1/61 排第一，weighted 下 chunk 11 排第一（bm25 独占高分），可区分两种融合路径。
    """
    bm25_hits = [
        {"retrievalMode": "bm25", "chunkId": 11, "title": "BM25 独占", "score": 9.0},
        {"retrievalMode": "bm25", "chunkId": 12, "title": "双路命中", "score": 7.0},
    ]
    vector_hits = [
        {"retrievalMode": "vector", "chunkId": 12, "title": "双路命中（向量）", "score": 0.9},
        {"retrievalMode": "vector", "chunkId": 13, "title": "向量独占", "score": 0.7},
    ]

    monkeypatch.setattr(retrieval_service, "retrieve_chunks", lambda db, **kwargs: list(bm25_hits))
    monkeypatch.setattr(
        retrieval_service, "retrieve_vector_chunks", lambda db, **kwargs: list(vector_hits)
    )


def test_rrf_fuse_merges_same_chunk_from_both_lists_at_rank_one() -> None:
    bm25_hits = [
        {"retrievalMode": "bm25", "chunkId": 7, "title": "RAG 日志", "score": 3.0},
        {"retrievalMode": "bm25", "chunkId": 8, "title": "检索说明", "score": 2.0},
    ]
    vector_hits = [
        {"retrievalMode": "vector", "chunkId": 7, "title": "RAG 日志（向量）", "score": 0.8},
        {"retrievalMode": "vector", "chunkId": 9, "title": "向量说明", "score": 0.6},
    ]

    fused = rrf_fuse(bm25_hits, vector_hits, limit=5)

    assert len(fused) == 3
    assert fused[0]["chunkId"] == 7
    assert fused[0]["rrfScore"] == round(2 / (60 + 1), 4)
    assert fused[0]["retrievalMode"] == "hybrid"
    assert fused[0]["fusion"] == "rrf"
    assert fused[0]["matchedRetrievalModes"] == ["bm25", "vector"]
    assert fused[0]["title"] == "RAG 日志"
    assert fused[0]["score"] == 3.0


def test_rrf_fuse_scores_single_list_rank_one_hit() -> None:
    bm25_hits = [{"retrievalMode": "bm25", "chunkId": 3, "title": "BM25 专属", "score": 2.5}]
    vector_hits = [{"retrievalMode": "vector", "chunkId": 4, "title": "向量专属", "score": 0.7}]

    fused = rrf_fuse(bm25_hits, vector_hits, limit=2)

    assert [item["chunkId"] for item in fused] == [3, 4]
    assert fused[0]["rrfScore"] == round(1 / (60 + 1), 4)
    assert fused[0]["matchedRetrievalModes"] == ["bm25"]
    assert fused[1]["rrfScore"] == round(1 / (60 + 1), 4)
    assert fused[1]["matchedRetrievalModes"] == ["vector"]


def test_rrf_fuse_truncates_to_limit_and_drops_lowest() -> None:
    bm25_hits = [
        {"retrievalMode": "bm25", "chunkId": 1, "title": "chunk-1", "score": 5.0},
        {"retrievalMode": "bm25", "chunkId": 2, "title": "chunk-2", "score": 4.0},
        {"retrievalMode": "bm25", "chunkId": 3, "title": "chunk-3", "score": 3.0},
        {"retrievalMode": "bm25", "chunkId": 4, "title": "chunk-4", "score": 2.0},
        {"retrievalMode": "bm25", "chunkId": 5, "title": "chunk-5", "score": 1.0},
    ]
    vector_hits = [{"retrievalMode": "vector", "chunkId": 1, "title": "chunk-1（向量）", "score": 0.9}]

    fused = rrf_fuse(bm25_hits, vector_hits, limit=3)

    assert [item["chunkId"] for item in fused] == [1, 2, 3]
    assert fused[0]["rrfScore"] == round(2 / (60 + 1), 4)


def test_rrf_fuse_k_parameter_changes_scores() -> None:
    shared_bm25 = {"retrievalMode": "bm25", "chunkId": 1, "title": "双路命中", "score": 3.0}
    shared_vector = {"retrievalMode": "vector", "chunkId": 1, "title": "双路命中", "score": 0.8}

    fused_shared = rrf_fuse([shared_bm25], [shared_vector], limit=1, k=1)
    assert fused_shared[0]["rrfScore"] == round(2 / (1 + 1), 4)
    assert fused_shared[0]["rrfScore"] == 1.0

    vector_only_rank_one = {"retrievalMode": "vector", "chunkId": 2, "title": "向量专属", "score": 0.9}
    fused = rrf_fuse([shared_bm25], [vector_only_rank_one, shared_vector], limit=2, k=1)

    assert fused[0]["chunkId"] == 1
    assert fused[0]["rrfScore"] == round(1 / (1 + 1) + 1 / (1 + 2), 4)
    assert fused[1]["chunkId"] == 2
    assert fused[1]["rrfScore"] == round(1 / (1 + 1), 4)


def test_retrieve_hybrid_chunks_with_rrf_fusion_marks_output_and_ranks_both_list_chunk_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_hybrid_fetchers(monkeypatch)

    output = retrieve_hybrid_chunks(
        db=None,
        user_id=1,
        knowledge_base="kb",
        query="q",
        limit=3,
        fusion="rrf",
    )

    assert len(output) == 3
    assert output[0]["fusion"] == "rrf"
    assert output[0]["chunkId"] == 12
    assert output[0]["rrfScore"] == round(1 / (60 + 2) + 1 / (60 + 1), 4)
    assert output[0]["matchedRetrievalModes"] == ["bm25", "vector"]


def test_retrieve_hybrid_chunks_with_invalid_fusion_falls_back_to_weighted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_hybrid_fetchers(monkeypatch)

    output = retrieve_hybrid_chunks(
        db=None,
        user_id=1,
        knowledge_base="kb",
        query="q",
        limit=3,
        fusion="banana",
    )

    assert len(output) == 3
    assert output[0]["retrievalMode"] == "hybrid"
    assert "hybridScore" in output[0]
    assert "fusion" not in output[0]
    assert output[0]["chunkId"] == 11


def test_retrieve_hybrid_chunks_without_fusion_reads_hybrid_fusion_mode_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_hybrid_fetchers(monkeypatch)
    monkeypatch.setattr(retrieval_service, "HYBRID_FUSION_MODE", "rrf", raising=False)

    output = retrieve_hybrid_chunks(
        db=None,
        user_id=1,
        knowledge_base="kb",
        query="q",
        limit=3,
    )

    assert output[0].get("fusion") == "rrf"
    assert output[0]["chunkId"] == 12


def test_retrieve_hybrid_chunks_default_weighted_mode_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_hybrid_fetchers(monkeypatch)
    monkeypatch.setattr(retrieval_service, "HYBRID_FUSION_MODE", "weighted", raising=False)

    output = retrieve_hybrid_chunks(
        db=None,
        user_id=1,
        knowledge_base="kb",
        query="q",
        limit=3,
    )

    assert output[0]["retrievalMode"] == "hybrid"
    assert "hybridScore" in output[0]
    assert "fusion" not in output[0]
    assert output[0]["chunkId"] == 11
