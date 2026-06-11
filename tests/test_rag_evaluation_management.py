from backend_python.rag_evaluation import (
    filter_evaluation_cases,
    normalize_evaluation_case,
    run_evaluation_suite,
)


def test_normalize_evaluation_case_fills_defaults_and_lists_keywords() -> None:
    case = normalize_evaluation_case(
        {
            "id": "case-001",
            "query": "RAG quality",
            "knowledgeBase": "role_knowledge",
            "expectedTitle": "RAG quality metrics",
            "expectedKeywords": "Hit@K",
        }
    )

    assert case["id"] == "case-001"
    assert case["expectedKnowledgeBase"] == "role_knowledge"
    assert case["expectedPositionTag"] == ""
    assert case["expectedStage"] == ""
    assert case["expectedKeywords"] == ["Hit@K"]


def test_filter_evaluation_cases_by_knowledge_base_and_position_tag() -> None:
    cases = [
        {"id": "ai", "knowledgeBase": "role_knowledge", "expectedPositionTag": "ai_app_intern"},
        {"id": "py", "knowledgeBase": "role_knowledge", "expectedPositionTag": "python_backend_intern"},
        {"id": "qb", "knowledgeBase": "question_bank", "expectedPositionTag": "ai_app_intern"},
    ]

    filtered = filter_evaluation_cases(cases, knowledge_base="role_knowledge", position_tag="ai_app_intern")

    assert [case["id"] for case in filtered] == ["ai"]


def test_run_evaluation_suite_returns_summary_insights_and_metric_definitions() -> None:
    cases = [
        {
            "id": "rag-quality",
            "query": "RAG quality metrics",
            "knowledgeBase": "role_knowledge",
            "expectedTitle": "RAG quality metrics",
            "expectedKeywords": ["Hit@K", "MRR"],
            "expectedKnowledgeBase": "role_knowledge",
        }
    ]

    def retriever(case, mode, k):
        return [
            {
                "title": "RAG quality metrics",
                "content": "Hit@K and MRR measure retrieval quality.",
                "metadata": {"knowledgeBase": "role_knowledge"},
            }
        ]

    report = run_evaluation_suite(cases, modes=["bm25"], k=3, retriever=retriever)

    assert report["caseCount"] == 1
    assert report["metricDefinitions"]["hitAtK"]
    assert report["modes"]["bm25"]["summary"]["hitAtK"] == 1.0
    assert report["modes"]["bm25"]["caseInsights"][0]["caseId"] == "rag-quality"
    assert report["modes"]["bm25"]["caseInsights"][0]["level"] == "good"
