import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLE_PATH = ROOT / "data" / "role_knowledge_seed.json"
QUESTION_PATH = ROOT / "data" / "question_bank_seed.json"
CASE_PATH = ROOT / "data" / "rag_evaluation_cases.json"

ROLE_IDS = {
    "predeploy_rag_query_rewrite",
    "predeploy_rag_chunk_metadata",
    "predeploy_rag_quality_dashboard",
    "predeploy_agent_rag_collaboration",
    "predeploy_backend_error_logging",
    "predeploy_deployment_readiness",
}

QUESTION_IDS = {
    "qb_predeploy_rag_001",
    "qb_predeploy_rag_002",
    "qb_predeploy_rag_003",
    "qb_predeploy_agent_001",
    "qb_predeploy_backend_001",
    "qb_predeploy_deploy_001",
}

CASE_IDS = {
    "eval_predeploy_rag_query_rewrite",
    "eval_predeploy_rag_chunk_metadata",
    "eval_predeploy_rag_quality_dashboard",
    "eval_predeploy_agent_rag_collaboration",
    "eval_predeploy_backend_error_logging",
    "eval_predeploy_deployment_readiness",
}


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def by_id(items: list[dict]) -> dict[str, dict]:
    return {str(item["id"]): item for item in items}


def test_pre_deployment_role_knowledge_entries_are_complete() -> None:
    items = by_id(load_json(ROLE_PATH))
    assert ROLE_IDS.issubset(items)

    for item_id in ROLE_IDS:
        item = items[item_id]
        assert item["role"] in {"AI 应用开发实习生", "Python 后端开发实习生"}
        assert item["category"]
        assert item["title"]
        assert isinstance(item["keywords"], list) and len(item["keywords"]) >= 6
        assert len(item["content"]) >= 100
        assert isinstance(item["follow_up_questions"], list) and len(item["follow_up_questions"]) >= 3
        assert isinstance(item["scoring_points"], list) and len(item["scoring_points"]) >= 4
        assert isinstance(item["risk_signals"], list) and len(item["risk_signals"]) >= 3


def test_pre_deployment_question_bank_entries_are_complete() -> None:
    items = by_id(load_json(QUESTION_PATH))
    assert QUESTION_IDS.issubset(items)

    for item_id in QUESTION_IDS:
        item = items[item_id]
        assert item["position_tag"] in {"ai_app_intern", "python_backend_intern"}
        assert item["category"] in {"technical", "project", "scenario", "system_design", "behavioral"}
        assert item["difficulty"] in {"basic", "medium", "hard"}
        assert len(item["question"]) >= 20
        assert len(item["reference_answer"]) >= 60
        assert isinstance(item["key_points"], list) and len(item["key_points"]) >= 4
        assert isinstance(item["tags"], list) and len(item["tags"]) >= 4


def test_pre_deployment_evaluation_cases_are_complete() -> None:
    cases = by_id(load_json(CASE_PATH))
    assert CASE_IDS.issubset(cases)

    for case_id in CASE_IDS:
        case = cases[case_id]
        assert case["knowledgeBase"] == "role_knowledge"
        assert case["expectedKnowledgeBase"] == "role_knowledge"
        assert case["expectedTitle"]
        assert isinstance(case["expectedKeywords"], list) and len(case["expectedKeywords"]) >= 4
