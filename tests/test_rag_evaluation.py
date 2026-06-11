import json
from pathlib import Path

from backend_python.rag_evaluation import (
    build_failure_analysis,
    calculate_hit_at_k,
    calculate_keyword_coverage,
    calculate_reciprocal_rank,
    evaluate_case,
    evaluate_modes,
    classify_case_result,
    summarize_mode_results,
)


def test_rag_evaluation_cases_have_required_fields() -> None:
    path = Path("data/rag_evaluation_cases.json")
    cases = json.loads(path.read_text(encoding="utf-8"))

    assert len(cases) >= 12
    groups = {item["knowledgeBase"] for item in cases}
    assert {"role_knowledge", "question_bank", "candidate_memory"}.issubset(groups)
    for item in cases:
        assert item["id"]
        assert item["query"]
        assert item["knowledgeBase"] in {"role_knowledge", "question_bank", "candidate_memory"}
        assert item["expectedTitle"]
        assert isinstance(item["expectedKeywords"], list)
        assert item["expectedKnowledgeBase"]


def test_calculate_hit_at_k_detects_expected_title_in_top_k() -> None:
    hits = [
        {"title": "FastAPI 模块化", "content": "APIRouter routes service"},
        {"title": "RAG 日志工程化", "content": "query_text hit_count"},
    ]

    assert calculate_hit_at_k(hits, "RAG 日志工程化", ["quality"], 2) == 1
    assert calculate_hit_at_k(hits, "RAG 日志工程化", ["quality"], 1) == 0


def test_calculate_reciprocal_rank_uses_first_expected_hit_rank() -> None:
    hits = [
        {"title": "FastAPI 模块化", "content": "APIRouter"},
        {"title": "RAG 日志工程化", "content": "query_text"},
    ]

    assert calculate_reciprocal_rank(hits, "RAG 日志工程化", ["query_text"]) == 0.5


def test_calculate_keyword_coverage_uses_top_k_content() -> None:
    hits = [
        {"title": "RAG 日志工程化", "content": "query_text hit_count quality"},
        {"title": "其它", "content": "retriever_name"},
    ]

    assert calculate_keyword_coverage(hits, ["query_text", "retriever_name", "hit_count", "quality"], 1) == 0.75
    assert calculate_keyword_coverage(hits, ["query_text", "retriever_name", "hit_count", "quality"], 2) == 1.0


def test_evaluate_case_returns_metrics_and_top_titles() -> None:
    case = {
        "id": "rag_log_fields",
        "query": "RAG 日志字段",
        "knowledgeBase": "role_knowledge",
        "expectedKnowledgeBase": "role_knowledge",
        "expectedPositionTag": "ai_app_intern",
        "expectedStage": "技术追问",
        "expectedTitle": "RAG 日志工程化",
        "expectedKeywords": ["query_text", "hit_count"],
    }
    hits = [
        {
            "title": "RAG 日志工程化",
            "content": "query_text",
            "metadata": {
                "knowledgeBase": "role_knowledge",
                "positionTag": "ai_app_intern",
                "interviewStage": "技术追问",
            },
        },
        {"title": "其它", "content": "hit_count"},
    ]

    result = evaluate_case(case, hits, k=2)

    assert result["caseId"] == "rag_log_fields"
    assert result["hitAtK"] == 1
    assert result["reciprocalRank"] == 1.0
    assert result["keywordCoverage"] == 1.0
    assert result["metadataMatch"] == 1
    assert result["emptyRecall"] == 0
    assert result["topTitles"] == ["RAG 日志工程化", "其它"]


def test_evaluate_case_marks_empty_recall_and_metadata_miss() -> None:
    case = {
        "id": "candidate-memory-001",
        "query": "候选人历史薄弱点",
        "knowledgeBase": "candidate_memory",
        "expectedKnowledgeBase": "candidate_memory",
        "expectedPositionTag": "ai_app_intern",
        "expectedStage": "技术追问",
        "expectedTitle": "RAG 薄弱点",
        "expectedKeywords": ["薄弱点"],
    }

    empty = evaluate_case(case, [], k=3)
    miss = evaluate_case(
        case,
        [{"title": "其它", "content": "薄弱点", "metadata": {"knowledgeBase": "role_knowledge"}}],
        k=3,
    )

    assert empty["emptyRecall"] == 1
    assert empty["metadataMatch"] == 0
    assert miss["emptyRecall"] == 0
    assert miss["metadataMatch"] == 0


def test_summarize_mode_results_averages_metrics() -> None:
    summary = summarize_mode_results(
        [
            {"hitAtK": 1, "reciprocalRank": 1.0, "keywordCoverage": 0.5},
            {"hitAtK": 0, "reciprocalRank": 0.0, "keywordCoverage": 0.25},
        ]
    )

    assert summary == {
        "caseCount": 2,
        "hitAtK": 0.5,
        "mrr": 0.5,
        "keywordCoverage": 0.375,
        "metadataMatchRate": 0.0,
        "emptyRecallRate": 0.0,
    }


def test_classify_case_result_explains_failure_reason() -> None:
    assert classify_case_result({"emptyRecall": 1, "metadataMatch": 0, "hitAtK": 0, "keywordCoverage": 0.0}) == "empty_recall"
    assert classify_case_result({"emptyRecall": 0, "metadataMatch": 0, "hitAtK": 0, "keywordCoverage": 0.0}) == "metadata_miss"
    assert classify_case_result({"emptyRecall": 0, "metadataMatch": 1, "hitAtK": 0, "keywordCoverage": 0.0}) == "missed_expected_hit"
    assert classify_case_result({"emptyRecall": 0, "metadataMatch": 1, "hitAtK": 1, "keywordCoverage": 0.25}) == "weak_keyword_coverage"
    assert classify_case_result({"emptyRecall": 0, "metadataMatch": 1, "hitAtK": 1, "keywordCoverage": 0.75}) == "ok"


def test_build_failure_analysis_groups_failed_cases() -> None:
    analysis = build_failure_analysis(
        [
            {"caseId": "empty", "emptyRecall": 1, "metadataMatch": 0, "hitAtK": 0, "keywordCoverage": 0.0},
            {"caseId": "metadata", "emptyRecall": 0, "metadataMatch": 0, "hitAtK": 0, "keywordCoverage": 0.0},
            {"caseId": "miss", "emptyRecall": 0, "metadataMatch": 1, "hitAtK": 0, "keywordCoverage": 0.0},
            {"caseId": "weak", "emptyRecall": 0, "metadataMatch": 1, "hitAtK": 1, "keywordCoverage": 0.25},
            {"caseId": "ok", "emptyRecall": 0, "metadataMatch": 1, "hitAtK": 1, "keywordCoverage": 1.0},
        ]
    )

    assert analysis["totalFailureCount"] == 4
    assert analysis["byReason"]["empty_recall"]["caseIds"] == ["empty"]
    assert analysis["byReason"]["metadata_miss"]["caseIds"] == ["metadata"]
    assert analysis["byReason"]["missed_expected_hit"]["caseIds"] == ["miss"]
    assert analysis["byReason"]["weak_keyword_coverage"]["caseIds"] == ["weak"]


def test_evaluate_modes_includes_failure_analysis() -> None:
    cases = [
        {
            "id": "empty",
            "query": "missing",
            "knowledgeBase": "role_knowledge",
            "expectedTitle": "Missing",
            "expectedKeywords": ["Missing"],
        }
    ]

    result = evaluate_modes(cases, modes=["bm25"], k=3, retriever=lambda case, mode, k: [])

    assert result["modes"]["bm25"]["failureAnalysis"]["totalFailureCount"] == 1
    assert result["modes"]["bm25"]["failureAnalysis"]["byReason"]["empty_recall"]["count"] == 1
