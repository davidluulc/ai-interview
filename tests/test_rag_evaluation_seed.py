from sqlalchemy import select

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument
from backend_python.rag_evaluation_seed import EVALUATION_SEED_DOCUMENTS, seed_evaluation_documents


def test_evaluation_seed_documents_match_expected_cases() -> None:
    ids = {item["caseId"] for item in EVALUATION_SEED_DOCUMENTS}
    groups = {}
    for item in EVALUATION_SEED_DOCUMENTS:
        groups[item["knowledgeBase"]] = groups.get(item["knowledgeBase"], 0) + 1

    assert {
        "rag_log_fields",
        "fastapi_module_split",
        "hybrid_search_reason",
        "rerank_fallback",
        "interview_follow_up",
    }.issubset(ids)
    assert len(EVALUATION_SEED_DOCUMENTS) >= 12
    assert groups["role_knowledge"] >= 4
    assert groups["question_bank"] >= 4
    assert groups["candidate_memory"] >= 4
    assert all(item["title"] and item["content"] for item in EVALUATION_SEED_DOCUMENTS)


def test_seed_evaluation_documents_creates_documents_and_ready_chunks() -> None:
    with SessionLocal() as db:
        user_id = 990001
        created = seed_evaluation_documents(db, user_id=user_id)

        documents = db.scalars(select(RagDocument).where(RagDocument.user_id == user_id)).all()
        chunks = db.scalars(select(RagChunk).where(RagChunk.user_id == user_id)).all()

    assert created == len(EVALUATION_SEED_DOCUMENTS)
    assert len(documents) >= len(EVALUATION_SEED_DOCUMENTS)
    assert len(chunks) >= len(EVALUATION_SEED_DOCUMENTS)
    assert all(chunk.embedding_status == "ready" for chunk in chunks)
    assert all(chunk.embedding_json != "[]" for chunk in chunks)
