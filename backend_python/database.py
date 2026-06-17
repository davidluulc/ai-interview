from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import AUTO_INIT_DB, DATABASE_URL


def build_connect_args(database_url: str) -> dict:
    return {"check_same_thread": False} if str(database_url or "").startswith("sqlite") else {}


def build_engine_options(database_url: str) -> dict:
    options = {"connect_args": build_connect_args(database_url)}
    if not str(database_url or "").startswith("sqlite"):
        options["pool_pre_ping"] = True
    return options


def mask_database_url(database_url: str) -> str:
    from .infrastructure import mask_service_url

    return mask_service_url(database_url)


def describe_database_url(database_url: str, *, auto_init: bool = AUTO_INIT_DB) -> dict:
    raw = str(database_url or "")
    dialect = raw.split(":", 1)[0] if ":" in raw else raw
    is_local_sqlite = raw.startswith("sqlite")
    auto_init_enabled = should_auto_init_db(auto_init=auto_init, database_url=raw)
    return {
        "dialect": dialect,
        "isLocalSqlite": is_local_sqlite,
        "usesExternalService": not is_local_sqlite,
        "autoInitEnabled": auto_init_enabled,
        "migrationTool": "metadata_create_all_for_local_sqlite" if auto_init_enabled else "alembic",
        "maskedUrl": mask_database_url(raw),
    }


def should_auto_init_db(*, auto_init: bool = AUTO_INIT_DB, database_url: str = DATABASE_URL) -> bool:
    return bool(auto_init) and str(database_url or "").startswith("sqlite")


connect_args = build_connect_args(DATABASE_URL)
engine = create_engine(DATABASE_URL, **build_engine_options(DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_compatibility_schema()


def ensure_sqlite_compatibility_schema() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = inspector.get_table_names()
        if "users" in table_names:
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "role" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)"))

        if "application_profiles" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE application_profiles (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        target_role VARCHAR(200) NOT NULL DEFAULT '',
                        application_type VARCHAR(100) NOT NULL DEFAULT '',
                        resume TEXT NOT NULL DEFAULT '',
                        jd TEXT NOT NULL DEFAULT '',
                        company TEXT NOT NULL DEFAULT '',
                        position_tag VARCHAR(100) NOT NULL DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users (id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_application_profiles_id ON application_profiles (id)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_application_profiles_user_id ON application_profiles (user_id)")
            )

        if "rag_retrieval_logs" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE rag_retrieval_logs (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        application_profile_id INTEGER,
                        interview_record_id INTEGER,
                        request_type VARCHAR(50) NOT NULL,
                        query_text TEXT NOT NULL DEFAULT '',
                        retriever_name VARCHAR(100) NOT NULL,
                        retrieval_mode VARCHAR(50) NOT NULL DEFAULT 'keyword',
                        hit_count INTEGER NOT NULL DEFAULT 0,
                        hits_json TEXT NOT NULL DEFAULT '[]',
                        used_in_prompt INTEGER NOT NULL DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users (id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_retrieval_logs_id ON rag_retrieval_logs (id)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_retrieval_logs_user_id ON rag_retrieval_logs (user_id)")
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_rag_retrieval_logs_application_profile_id "
                    "ON rag_retrieval_logs (application_profile_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_rag_retrieval_logs_interview_record_id "
                    "ON rag_retrieval_logs (interview_record_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_rag_retrieval_logs_request_type "
                    "ON rag_retrieval_logs (request_type)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_rag_retrieval_logs_retriever_name "
                    "ON rag_retrieval_logs (retriever_name)"
                )
            )

        if "agent_decision_logs" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE agent_decision_logs (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        application_profile_id INTEGER,
                        request_type VARCHAR(50) NOT NULL,
                        next_action VARCHAR(50) NOT NULL,
                        stage VARCHAR(100) NOT NULL DEFAULT '',
                        difficulty VARCHAR(50) NOT NULL DEFAULT '',
                        focus VARCHAR(200) NOT NULL DEFAULT '',
                        reason TEXT NOT NULL DEFAULT '',
                        tools_json TEXT NOT NULL DEFAULT '[]',
                        state_json TEXT NOT NULL DEFAULT '{}',
                        decision_json TEXT NOT NULL DEFAULT '{}',
                        fallback_used INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users (id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_decision_logs_id ON agent_decision_logs (id)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_agent_decision_logs_user_id ON agent_decision_logs (user_id)")
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_agent_decision_logs_application_profile_id "
                    "ON agent_decision_logs (application_profile_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_agent_decision_logs_request_type "
                    "ON agent_decision_logs (request_type)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_agent_decision_logs_next_action "
                    "ON agent_decision_logs (next_action)"
                )
            )

        if "rag_documents" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE rag_documents (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        title VARCHAR(200) NOT NULL,
                        knowledge_base VARCHAR(50) NOT NULL,
                        source_type VARCHAR(50) NOT NULL DEFAULT 'manual',
                        status VARCHAR(40) NOT NULL DEFAULT 'enabled',
                        visibility VARCHAR(40) NOT NULL DEFAULT 'private',
                        content_hash VARCHAR(64) NOT NULL DEFAULT '',
                        content TEXT NOT NULL DEFAULT '',
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        chunk_count INTEGER NOT NULL DEFAULT 0,
                        duplicate_chunk_count INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users (id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_documents_id ON rag_documents (id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_documents_user_id ON rag_documents (user_id)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_documents_knowledge_base ON rag_documents (knowledge_base)")
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_documents_status ON rag_documents (status)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_documents_visibility ON rag_documents (visibility)")
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_documents_content_hash ON rag_documents (content_hash)")
            )
        elif "rag_documents" in table_names:
            document_columns = {column["name"] for column in inspector.get_columns("rag_documents")}
            if "status" not in document_columns:
                connection.execute(
                    text("ALTER TABLE rag_documents ADD COLUMN status VARCHAR(40) NOT NULL DEFAULT 'enabled'")
                )
            if "visibility" not in document_columns:
                connection.execute(
                    text("ALTER TABLE rag_documents ADD COLUMN visibility VARCHAR(40) NOT NULL DEFAULT 'private'")
                )
            if "content_hash" not in document_columns:
                connection.execute(
                    text("ALTER TABLE rag_documents ADD COLUMN content_hash VARCHAR(64) NOT NULL DEFAULT ''")
                )
            if "duplicate_chunk_count" not in document_columns:
                connection.execute(
                    text("ALTER TABLE rag_documents ADD COLUMN duplicate_chunk_count INTEGER NOT NULL DEFAULT 0")
                )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_documents_status ON rag_documents (status)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_documents_visibility ON rag_documents (visibility)")
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_documents_content_hash ON rag_documents (content_hash)")
            )

        if "rag_chunks" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE rag_chunks (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        document_id INTEGER NOT NULL,
                        knowledge_base VARCHAR(50) NOT NULL,
                        title VARCHAR(200) NOT NULL DEFAULT '',
                        content TEXT NOT NULL DEFAULT '',
                        chunk_index INTEGER NOT NULL DEFAULT 0,
                        chunk_hash VARCHAR(64) NOT NULL DEFAULT '',
                        is_duplicate INTEGER NOT NULL DEFAULT 0,
                        keywords_json TEXT NOT NULL DEFAULT '[]',
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        embedding_json TEXT NOT NULL DEFAULT '[]',
                        embedding_model VARCHAR(100) NOT NULL DEFAULT '',
                        embedding_status VARCHAR(50) NOT NULL DEFAULT 'pending',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users (id),
                        FOREIGN KEY(document_id) REFERENCES rag_documents (id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_id ON rag_chunks (id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_user_id ON rag_chunks (user_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_document_id ON rag_chunks (document_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_knowledge_base ON rag_chunks (knowledge_base)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_chunk_hash ON rag_chunks (chunk_hash)"))
        elif "rag_chunks" in table_names:
            chunk_columns = {column["name"] for column in inspector.get_columns("rag_chunks")}
            if "chunk_hash" not in chunk_columns:
                connection.execute(text("ALTER TABLE rag_chunks ADD COLUMN chunk_hash VARCHAR(64) NOT NULL DEFAULT ''"))
            if "is_duplicate" not in chunk_columns:
                connection.execute(text("ALTER TABLE rag_chunks ADD COLUMN is_duplicate INTEGER NOT NULL DEFAULT 0"))
            if "embedding_json" not in chunk_columns:
                connection.execute(text("ALTER TABLE rag_chunks ADD COLUMN embedding_json TEXT NOT NULL DEFAULT '[]'"))
            if "embedding_model" not in chunk_columns:
                connection.execute(text("ALTER TABLE rag_chunks ADD COLUMN embedding_model VARCHAR(100) NOT NULL DEFAULT ''"))
            if "embedding_status" not in chunk_columns:
                connection.execute(
                    text("ALTER TABLE rag_chunks ADD COLUMN embedding_status VARCHAR(50) NOT NULL DEFAULT 'pending'")
                )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_chunk_hash ON rag_chunks (chunk_hash)"))

        if "rag_ingestion_tasks" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE rag_ingestion_tasks (
                        id INTEGER NOT NULL PRIMARY KEY,
                        task_id VARCHAR(120) NOT NULL,
                        user_id INTEGER NOT NULL,
                        document_id INTEGER,
                        knowledge_base VARCHAR(50) NOT NULL DEFAULT '',
                        title VARCHAR(200) NOT NULL DEFAULT '',
                        original_filename VARCHAR(255) NOT NULL DEFAULT '',
                        source_extension VARCHAR(20) NOT NULL DEFAULT '',
                        status VARCHAR(40) NOT NULL DEFAULT 'pending',
                        progress INTEGER NOT NULL DEFAULT 0,
                        message VARCHAR(255) NOT NULL DEFAULT '',
                        error_message TEXT NOT NULL DEFAULT '',
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        max_retries INTEGER NOT NULL DEFAULT 2,
                        can_retry INTEGER NOT NULL DEFAULT 0,
                        preview_json TEXT NOT NULL DEFAULT '{}',
                        result_json TEXT NOT NULL DEFAULT '{}',
                        input_json TEXT NOT NULL DEFAULT '{}',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        completed_at DATETIME,
                        FOREIGN KEY(user_id) REFERENCES users (id),
                        FOREIGN KEY(document_id) REFERENCES rag_documents (id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_ingestion_tasks_id ON rag_ingestion_tasks (id)"))
            connection.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_rag_ingestion_tasks_task_id ON rag_ingestion_tasks (task_id)")
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_ingestion_tasks_user_id ON rag_ingestion_tasks (user_id)")
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_ingestion_tasks_document_id ON rag_ingestion_tasks (document_id)")
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_ingestion_tasks_status ON rag_ingestion_tasks (status)")
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_rag_ingestion_tasks_can_retry ON rag_ingestion_tasks (can_retry)")
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_rag_ingestion_tasks_knowledge_base "
                    "ON rag_ingestion_tasks (knowledge_base)"
                )
            )

        if "training_tasks" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE training_tasks (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        application_profile_id INTEGER,
                        source_interview_record_id INTEGER,
                        weak_tag VARCHAR(80) NOT NULL,
                        weak_label VARCHAR(120) NOT NULL DEFAULT '',
                        title VARCHAR(200) NOT NULL DEFAULT '',
                        description TEXT NOT NULL DEFAULT '',
                        status VARCHAR(40) NOT NULL DEFAULT 'todo',
                        priority VARCHAR(40) NOT NULL DEFAULT 'medium',
                        mastery_score INTEGER NOT NULL DEFAULT 40,
                        attempt_count INTEGER NOT NULL DEFAULT 0,
                        last_practiced_at DATETIME,
                        next_review_at DATETIME,
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users (id),
                        FOREIGN KEY(application_profile_id) REFERENCES application_profiles (id),
                        FOREIGN KEY(source_interview_record_id) REFERENCES interview_records (id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_id ON training_tasks (id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_user_id ON training_tasks (user_id)"))
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_training_tasks_application_profile_id "
                    "ON training_tasks (application_profile_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_training_tasks_source_interview_record_id "
                    "ON training_tasks (source_interview_record_id)"
                )
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_weak_tag ON training_tasks (weak_tag)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_status ON training_tasks (status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_training_tasks_priority ON training_tasks (priority)"))

        if "langgraph_checkpoint_summaries" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE langgraph_checkpoint_summaries (
                        id INTEGER NOT NULL PRIMARY KEY,
                        thread_id VARCHAR(200) NOT NULL,
                        runtime VARCHAR(50) NOT NULL DEFAULT 'langgraph',
                        status VARCHAR(50) NOT NULL DEFAULT 'completed',
                        current_node VARCHAR(100) NOT NULL DEFAULT '',
                        round_count INTEGER NOT NULL DEFAULT 0,
                        last_action VARCHAR(80) NOT NULL DEFAULT '',
                        last_question TEXT NOT NULL DEFAULT '',
                        requires_human_review INTEGER NOT NULL DEFAULT 0,
                        interrupt_json TEXT NOT NULL DEFAULT '',
                        resume_decision TEXT NOT NULL DEFAULT '',
                        runtime_trace_json TEXT NOT NULL DEFAULT '[]',
                        quality_gate_json TEXT NOT NULL DEFAULT '{}',
                        comparison_json TEXT NOT NULL DEFAULT '{}',
                        raw_summary_json TEXT NOT NULL DEFAULT '{}',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_langgraph_checkpoint_summaries_id "
                    "ON langgraph_checkpoint_summaries (id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_langgraph_checkpoint_summaries_thread_id "
                    "ON langgraph_checkpoint_summaries (thread_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_langgraph_checkpoint_summaries_runtime "
                    "ON langgraph_checkpoint_summaries (runtime)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_langgraph_checkpoint_summaries_status "
                    "ON langgraph_checkpoint_summaries (status)"
                )
            )

        if "interview_records" not in table_names:
            return

        columns = {column["name"] for column in inspector.get_columns("interview_records")}
        if "user_id" not in columns:
            connection.execute(text("ALTER TABLE interview_records ADD COLUMN user_id INTEGER"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_interview_records_user_id ON interview_records (user_id)"))
        if "application_profile_id" not in columns:
            connection.execute(text("ALTER TABLE interview_records ADD COLUMN application_profile_id INTEGER"))
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_interview_records_application_profile_id "
                    "ON interview_records (application_profile_id)"
                )
            )
