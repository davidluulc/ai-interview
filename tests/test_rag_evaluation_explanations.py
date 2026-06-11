from backend_python.rag_evaluation import build_case_insight, explain_evaluation_metrics


def test_explain_evaluation_metrics_returns_chinese_learning_text() -> None:
    explanations = explain_evaluation_metrics()

    assert "hitAtK" in explanations
    assert "MRR" in explanations["mrr"]
    assert "关键词覆盖率" in explanations["keywordCoverage"]
    assert "metadata" in explanations["metadataMatch"]
    assert "空召回" in explanations["emptyRecall"]


def test_build_case_insight_marks_successful_case() -> None:
    insight = build_case_insight(
        {
            "caseId": "case_ok",
            "query": "RAG 质量评估指标有哪些？",
            "hitAtK": 1,
            "reciprocalRank": 1.0,
            "keywordCoverage": 0.75,
            "metadataMatch": 1,
            "emptyRecall": 0,
            "topTitles": ["RAG 质量评估与可观测面板"],
        }
    )

    assert insight["level"] == "good"
    assert "命中预期资料" in insight["summary"]
    assert "RAG 质量评估与可观测面板" in insight["evidence"]


def test_build_case_insight_marks_weak_case_with_action() -> None:
    insight = build_case_insight(
        {
            "caseId": "case_weak",
            "query": "RAG metadata 权限怎么做？",
            "hitAtK": 0,
            "reciprocalRank": 0.0,
            "keywordCoverage": 0.25,
            "metadataMatch": 0,
            "emptyRecall": 0,
            "topTitles": ["无关资料"],
        }
    )

    assert insight["level"] == "weak"
    assert "未命中预期资料" in insight["summary"]
    assert "补充 seed" in insight["action"]
