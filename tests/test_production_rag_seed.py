from uuid import uuid4
from pathlib import Path

from backend_python.database import SessionLocal
from backend_python.db_models import RagChunk, RagDocument, User
from backend_python.production_rag_seed import run_production_rag_seed
from backend_python.rag_store import parse_json


def create_seed_user(db) -> User:
    suffix = uuid4().hex
    user = User(
        email=f"production-seed-{suffix}@example.com",
        username=f"production_seed_{suffix[:10]}",
        password_hash="hash",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def fake_embed_text(text: str) -> list[float]:
    return [0.1, 0.2, 0.3]


def test_seed_production_rag_creates_role_and_question_chunks(monkeypatch) -> None:
    monkeypatch.setattr("backend_python.production_rag_seed.current_embedding_model", lambda: "embedding-3")
    monkeypatch.setattr("backend_python.production_rag_seed.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_seed_user(db)

        summary = run_production_rag_seed(db, user_id=user.id)

        role_ready_count = (
            db.query(RagChunk)
            .filter(
                RagChunk.user_id == user.id,
                RagChunk.knowledge_base == "role_knowledge",
                RagChunk.embedding_model == "embedding-3",
                RagChunk.embedding_status == "ready",
            )
            .count()
        )
        question_ready_count = (
            db.query(RagChunk)
            .filter(
                RagChunk.user_id == user.id,
                RagChunk.knowledge_base == "question_bank",
                RagChunk.embedding_model == "embedding-3",
                RagChunk.embedding_status == "ready",
            )
            .count()
        )

    assert summary["createdDocuments"] >= 2
    assert summary["readyChunks"] == role_ready_count + question_ready_count
    assert role_ready_count > 0
    assert question_ready_count > 0


def test_seed_production_rag_is_idempotent_by_seed_key(monkeypatch) -> None:
    monkeypatch.setattr("backend_python.production_rag_seed.current_embedding_model", lambda: "embedding-3")
    monkeypatch.setattr("backend_python.production_rag_seed.embed_text", fake_embed_text)

    with SessionLocal() as db:
        user = create_seed_user(db)

        first_summary = run_production_rag_seed(db, user_id=user.id)
        first_documents = (
            db.query(RagDocument)
            .filter(RagDocument.user_id == user.id, RagDocument.source_type == "production_seed")
            .count()
        )
        second_summary = run_production_rag_seed(db, user_id=user.id)
        second_documents = (
            db.query(RagDocument)
            .filter(RagDocument.user_id == user.id, RagDocument.source_type == "production_seed")
            .count()
        )

        seed_keys = [
            parse_json(document.metadata_json, {}).get("seedKey")
            for document in db.query(RagDocument)
            .filter(RagDocument.user_id == user.id, RagDocument.source_type == "production_seed")
            .all()
        ]

    assert first_summary["createdDocuments"] > 0
    assert second_summary["createdDocuments"] == 0
    assert second_summary["skippedDocuments"] == first_documents
    assert second_documents == first_documents
    assert len(seed_keys) == len(set(seed_keys))


def test_seed_cli_bootstraps_project_root_before_backend_imports() -> None:
    script_text = Path("scripts/seed_production_rag.py").read_text(encoding="utf-8")

    assert "sys.path.insert(0, str(ROOT_DIR))" in script_text
    assert script_text.index("sys.path.insert") < script_text.index("from backend_python.database")
