import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLE_PATH = ROOT / "data" / "role_knowledge_seed.json"
QUESTION_PATH = ROOT / "data" / "question_bank_seed.json"
CASE_PATH = ROOT / "data" / "rag_evaluation_cases.json"

PY_ROLE_IDS = {
    "py_backend_v2_python_async",
    "py_backend_v2_http_status",
    "py_backend_v2_fastapi_depends",
    "py_backend_v2_pydantic_schema",
    "py_backend_v2_sqlalchemy_relationship",
    "py_backend_v2_transaction_alembic",
    "py_backend_v2_jwt_refresh_token",
    "py_backend_v2_user_data_isolation",
    "py_backend_v2_logging_testing",
    "py_backend_v2_uvicorn_nginx_deploy",
}

AI_ROLE_IDS = {
    "ai_app_v2_llm_api_params",
    "ai_app_v2_prompt_template",
    "ai_app_v2_rag_pipeline",
    "ai_app_v2_bm25_vector_hybrid",
    "ai_app_v2_rerank_eval",
    "ai_app_v2_three_rags_boundary",
    "ai_app_v2_agent_state_decision",
    "ai_app_v2_toolcalls_trace",
    "ai_app_v2_guardrails_fallback",
    "ai_app_v2_frontier_langgraph_mcp",
}

PY_QUESTION_IDS = {f"qb_py_v2_{index:03d}" for index in range(1, 11)}
AI_QUESTION_IDS = {f"qb_ai_v2_{index:03d}" for index in range(1, 11)}
PY_EVAL_IDS = {f"eval_py_backend_v2_{index:03d}" for index in range(1, 11)}
AI_EVAL_IDS = {f"eval_ai_app_v2_{index:03d}" for index in range(1, 11)}


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_unique_ids(items: list[dict], key: str = "id") -> None:
    counts = Counter(str(item.get(key) or "") for item in items)
    duplicates = sorted(item_id for item_id, count in counts.items() if count > 1)
    assert not duplicates


def test_role_knowledge_v2_entries_exist_and_are_complete() -> None:
    items = load_json(ROLE_PATH)
    assert_unique_ids(items)
    by_id = {item["id"]: item for item in items}

    assert PY_ROLE_IDS.issubset(by_id)
    assert AI_ROLE_IDS.issubset(by_id)

    for item_id in PY_ROLE_IDS | AI_ROLE_IDS:
        item = by_id[item_id]
        assert item["role"] in {"Python 后端开发实习生", "AI 应用开发实习生"}
        assert item["category"]
        assert item["title"]
        assert isinstance(item["keywords"], list) and len(item["keywords"]) >= 5
        assert len(item["content"]) >= 80
        assert isinstance(item["follow_up_questions"], list) and len(item["follow_up_questions"]) >= 3
        assert isinstance(item["scoring_points"], list) and len(item["scoring_points"]) >= 4
        assert isinstance(item["risk_signals"], list) and len(item["risk_signals"]) >= 3


def test_question_bank_v2_entries_exist_and_are_complete() -> None:
    items = load_json(QUESTION_PATH)
    assert_unique_ids(items)
    by_id = {item["id"]: item for item in items}

    assert PY_QUESTION_IDS.issubset(by_id)
    assert AI_QUESTION_IDS.issubset(by_id)

    for item_id in PY_QUESTION_IDS:
        item = by_id[item_id]
        assert item["position_tag"] == "python_backend_intern"
        assert item["category"] in {"technical", "project", "scenario", "system_design", "behavioral"}
        assert item["difficulty"] in {"basic", "medium", "hard"}
        assert item["question"]
        assert len(item["reference_answer"]) >= 50
        assert isinstance(item["key_points"], list) and len(item["key_points"]) >= 4
        assert isinstance(item["tags"], list) and len(item["tags"]) >= 4

    for item_id in AI_QUESTION_IDS:
        item = by_id[item_id]
        assert item["position_tag"] == "ai_app_intern"
        assert item["category"] in {"technical", "project", "scenario", "system_design", "behavioral"}
        assert item["difficulty"] in {"basic", "medium", "hard"}
        assert item["question"]
        assert len(item["reference_answer"]) >= 50
        assert isinstance(item["key_points"], list) and len(item["key_points"]) >= 4
        assert isinstance(item["tags"], list) and len(item["tags"]) >= 4


def test_rag_evaluation_v2_cases_exist_and_are_complete() -> None:
    cases = load_json(CASE_PATH)
    assert_unique_ids(cases)
    by_id = {item["id"]: item for item in cases}

    assert PY_EVAL_IDS.issubset(by_id)
    assert AI_EVAL_IDS.issubset(by_id)

    for case_id in PY_EVAL_IDS:
        case = by_id[case_id]
        assert case["knowledgeBase"] == "role_knowledge"
        assert case["expectedKnowledgeBase"] == "role_knowledge"
        assert case["expectedPositionTag"] == "python_backend_intern"
        assert case["expectedTitle"]
        assert isinstance(case["expectedKeywords"], list) and len(case["expectedKeywords"]) >= 4

    for case_id in AI_EVAL_IDS:
        case = by_id[case_id]
        assert case["knowledgeBase"] == "role_knowledge"
        assert case["expectedKnowledgeBase"] == "role_knowledge"
        assert case["expectedPositionTag"] == "ai_app_intern"
        assert case["expectedTitle"]
        assert isinstance(case["expectedKeywords"], list) and len(case["expectedKeywords"]) >= 4
