from pathlib import Path

from backend_python.db_models import AgentDecisionLog, InterviewRecord, RagChunk


def test_interview_record_model_declares_expected_table_and_columns() -> None:
    columns = InterviewRecord.__table__.columns

    assert InterviewRecord.__tablename__ == "interview_records"
    assert "id" in columns
    assert "candidate_name" in columns
    assert "target_role" in columns
    assert "application_type" in columns
    assert "mode" in columns
    assert "depth" in columns
    assert "score" in columns
    assert "profile_json" in columns
    assert "answers_json" in columns
    assert "report_json" in columns
    assert "created_at" in columns


def test_alembic_configuration_files_exist() -> None:
    assert Path("alembic.ini").exists()
    assert Path("alembic/env.py").exists()
    assert Path("alembic/script.py.mako").exists()


def test_initial_interview_records_migration_exists() -> None:
    migration_files = list(Path("alembic/versions").glob("*create_interview_records.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text(encoding="utf-8")
    assert "create_table" in migration_text
    assert "interview_records" in migration_text
    assert "candidate_name" in migration_text
    assert "report_json" in migration_text


def test_rag_chunk_model_declares_embedding_columns() -> None:
    columns = RagChunk.__table__.columns

    assert "embedding_json" in columns
    assert "embedding_model" in columns
    assert "embedding_status" in columns


def test_rag_chunk_embedding_migration_exists() -> None:
    migration_files = list(Path("alembic/versions").glob("*add_rag_chunk_embeddings.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text(encoding="utf-8")
    assert "embedding_json" in migration_text
    assert "embedding_model" in migration_text
    assert "embedding_status" in migration_text


def test_rag_document_lifecycle_migration_exists() -> None:
    migration_files = list(Path("alembic/versions").glob("*add_rag_document_lifecycle_columns.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text(encoding="utf-8")
    for expected_column in [
        "status",
        "visibility",
        "content_hash",
        "duplicate_chunk_count",
        "chunk_hash",
        "is_duplicate",
    ]:
        assert expected_column in migration_text


def test_user_role_migration_is_safe_when_column_was_hotfixed() -> None:
    migration_files = list(Path("alembic/versions").glob("*add_user_role.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text(encoding="utf-8")
    assert "_add_column_if_missing" in migration_text
    assert "_create_index_if_missing" in migration_text
    assert "_drop_column_if_exists" in migration_text
    assert "_drop_index_if_exists" in migration_text


def test_agent_decision_log_model_declares_expected_columns() -> None:
    columns = AgentDecisionLog.__table__.columns

    assert "user_id" in columns
    assert "next_action" in columns
    assert "state_json" in columns
    assert "decision_json" in columns
    assert "fallback_used" in columns


def test_agent_decision_log_migration_exists() -> None:
    migration_files = list(Path("alembic/versions").glob("*add_agent_decision_logs.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text(encoding="utf-8")
    assert "agent_decision_logs" in migration_text
    assert "next_action" in migration_text
    assert "decision_json" in migration_text
    assert "fallback_used" in migration_text
