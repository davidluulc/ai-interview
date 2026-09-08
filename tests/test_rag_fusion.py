from backend_python.retrieval_service import rrf_fuse


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
