import json

from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument
from backend_python.rag_evaluation import evaluate_modes
from backend_python.rag_evaluation_seed import EVALUATION_SEED_DOCUMENTS
from scripts.run_rag_evaluation import (
    build_mock_query_embedding,
    ensure_evaluation_seed_documents,
    parse_args,
    render_result,
)


def test_evaluate_modes_runs_each_mode_and_isolates_failures() -> None:
    cases = [
        {
            "id": "case_1",
            "query": "RAG 日志字段",
            "knowledgeBase": "role_knowledge",
            "expectedTitle": "RAG 日志工程化",
            "expectedKeywords": ["query_text"],
        }
    ]

    def fake_retriever(case: dict, mode: str, k: int) -> list[dict]:
        if mode == "vector":
            raise RuntimeError("embedding failed")
        return [{"title": "RAG 日志工程化", "content": "query_text"}]

    result = evaluate_modes(cases, modes=["bm25", "vector"], k=3, retriever=fake_retriever)

    assert result["k"] == 3
    assert result["modes"]["bm25"]["summary"]["hitAtK"] == 1.0
    assert result["modes"]["vector"]["summary"]["caseCount"] == 0
    assert result["modes"]["vector"]["errors"][0]["caseId"] == "case_1"


def test_render_result_outputs_pretty_json() -> None:
    rendered = render_result({"k": 3, "modes": {"bm25": {"summary": {"hitAtK": 1.0}}}})

    data = json.loads(rendered)
    assert data["k"] == 3
    assert data["modes"]["bm25"]["summary"]["hitAtK"] == 1.0
    assert "\n" in rendered


def test_parse_args_supports_mock_vector_flag() -> None:
    args = parse_args(["--mock-vector"])

    assert args.mock_vector is True


def test_build_mock_query_embedding_matches_evaluation_case_intent() -> None:
    assert build_mock_query_embedding({"id": "rag_log_fields"}) == [1.0, 0.0, 0.0]
    assert build_mock_query_embedding({"id": "fastapi_module_split"}) == [0.0, 1.0, 0.0]
    assert build_mock_query_embedding({"id": "interview_follow_up"}) == [0.2, 0.4, 0.9]


def test_ensure_evaluation_seed_documents_rebuilds_target_user_docs() -> None:
    user_id = 990777

    with SessionLocal() as db:
        created = ensure_evaluation_seed_documents(db, user_id=user_id)
        documents = db.scalars(
            select(RagDocument).where(
                RagDocument.user_id == user_id,
                RagDocument.source_type == "evaluation_seed",
            )
        ).all()
        chunks = db.scalars(
            select(RagChunk).where(
                RagChunk.user_id == user_id,
                RagChunk.metadata_json.like('%"evaluation_seed"%'),
            )
        ).all()

    assert created == len(EVALUATION_SEED_DOCUMENTS)
    assert len(documents) == len(EVALUATION_SEED_DOCUMENTS)
    assert len(chunks) >= len(EVALUATION_SEED_DOCUMENTS)
    assert any(document.title == "FastAPI Depends 依赖注入" for document in documents)
