from backend_python.retrieval_service import apply_rerank_results, merge_hybrid_hits, normalize_hybrid_weights


def test_normalize_hybrid_weights_normalizes_positive_values() -> None:
    assert normalize_hybrid_weights({"bm25": 2, "vector": 1}) == {"bm25": 0.6667, "vector": 0.3333}


def test_merge_hybrid_hits_records_configured_weights() -> None:
    bm25_hits = [
        {
            "retrievalMode": "bm25",
            "chunkId": 1,
            "documentId": 10,
            "title": "BM25 match",
            "content": "keyword match",
            "score": 3.0,
            "matchedTokens": ["keyword"],
            "matchedKeywords": [],
            "metadata": {},
        }
    ]
    vector_hits = [
        {
            "retrievalMode": "vector",
            "chunkId": 2,
            "documentId": 20,
            "title": "Vector match",
            "content": "semantic match",
            "score": 0.9,
            "matchedTokens": [],
            "matchedKeywords": [],
            "metadata": {},
        }
    ]

    merged = merge_hybrid_hits(bm25_hits, vector_hits, limit=2, bm25_weight=0.8, vector_weight=0.2)

    assert merged[0]["hybridWeights"] == {"bm25": 0.8, "vector": 0.2}
    assert merged[1]["hybridWeights"] == {"bm25": 0.8, "vector": 0.2}


def test_apply_rerank_results_records_rank_change_and_explanation() -> None:
    hits = [
        {"chunkId": 1, "title": "A", "score": 0.8, "matchedRetrievalModes": ["bm25"], "hybridScore": 0.8},
        {"chunkId": 2, "title": "B", "score": 0.4, "matchedRetrievalModes": ["vector"], "hybridScore": 0.4},
    ]

    reranked = apply_rerank_results(
        hits,
        [
            {"index": 1, "relevance_score": 0.95},
            {"index": 0, "relevance_score": 0.55},
        ],
        limit=2,
    )

    assert reranked[0]["chunkId"] == 2
    assert reranked[0]["preRerankRank"] == 2
    assert reranked[0]["postRerankRank"] == 1
    assert reranked[0]["rankChange"] == 1
    assert "rerankScore=0.95" in reranked[0]["rerankExplanation"]
