from backend_python.rag_quality import evaluate_retrieval_quality, summarize_retrieval_sources


def test_evaluate_retrieval_quality_marks_miss_without_hits() -> None:
    quality = evaluate_retrieval_quality([])

    assert quality == {
        "level": "miss",
        "label": "未命中",
        "hitCount": 0,
        "maxScore": 0,
        "averageScore": 0,
        "databaseHitCount": 0,
        "seedHitCount": 0,
        "reason": "没有召回任何资料，模型只能依赖用户输入和通用能力。",
    }


def test_evaluate_retrieval_quality_marks_good_for_multiple_high_score_hits() -> None:
    quality = evaluate_retrieval_quality(
        [
            {"score": 12, "source": "database", "chunkId": 1},
            {"score": 8, "source": "database", "chunkId": 2},
            {"score": 5, "title": "seed item"},
        ]
    )

    assert quality["level"] == "good"
    assert quality["label"] == "命中良好"
    assert quality["hitCount"] == 3
    assert quality["maxScore"] == 12
    assert quality["averageScore"] == 8.33
    assert quality["databaseHitCount"] == 2
    assert quality["seedHitCount"] == 1


def test_evaluate_retrieval_quality_marks_good_for_single_strong_hit() -> None:
    quality = evaluate_retrieval_quality([{"score": 9, "title": "RAG 质量评估与可观测面板"}])

    assert quality["level"] == "good"
    assert quality["label"] == "命中良好"
    assert quality["hitCount"] == 1
    assert quality["maxScore"] == 9


def test_evaluate_retrieval_quality_marks_weak_for_low_score_hits() -> None:
    quality = evaluate_retrieval_quality([{"score": 1.2, "source": "database", "chunkId": 9}])

    assert quality["level"] == "weak"
    assert quality["label"] == "命中偏弱"
    assert quality["reason"] == "有召回资料，但命中数量或分数偏低，需要补充知识库或优化 query。"


def test_summarize_retrieval_sources_counts_database_and_seed_hits() -> None:
    summary = summarize_retrieval_sources(
        [
            {"source": "database", "chunkId": 1},
            {"source": "database", "chunkId": 2},
            {"title": "seed fallback"},
        ]
    )

    assert summary == {
        "databaseHitCount": 2,
        "seedHitCount": 1,
        "hasDatabaseHits": True,
        "hasSeedFallback": True,
    }
