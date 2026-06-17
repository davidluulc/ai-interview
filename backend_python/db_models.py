from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class InterviewRecord(Base):
    __tablename__ = "interview_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    application_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_profiles.id"),
        nullable=True,
        index=True,
    )
    candidate_name: Mapped[str] = mapped_column(String(100), default="")
    target_role: Mapped[str] = mapped_column(String(200), default="")
    application_type: Mapped[str] = mapped_column(String(100), default="")
    mode: Mapped[str] = mapped_column(String(100), default="")
    depth: Mapped[str] = mapped_column(String(50), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    profile_json: Mapped[str] = mapped_column(Text)
    answers_json: Mapped[str] = mapped_column(Text)
    report_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped["User | None"] = relationship(back_populates="interview_records")
    application_profile: Mapped["ApplicationProfile | None"] = relationship(back_populates="interview_records")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    interview_records: Mapped[list[InterviewRecord]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    application_profiles: Mapped[list["ApplicationProfile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    rag_retrieval_logs: Mapped[list["RagRetrievalLog"]] = relationship(back_populates="user")
    agent_decision_logs: Mapped[list["AgentDecisionLog"]] = relationship(back_populates="user")
    rag_documents: Mapped[list["RagDocument"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    rag_chunks: Mapped[list["RagChunk"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    rag_ingestion_tasks: Mapped[list["RagIngestionTask"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    training_tasks: Mapped[list["TrainingTask"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class ApplicationProfile(Base):
    __tablename__ = "application_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    target_role: Mapped[str] = mapped_column(String(200), default="")
    application_type: Mapped[str] = mapped_column(String(100), default="")
    resume: Mapped[str] = mapped_column(Text, default="")
    jd: Mapped[str] = mapped_column(Text, default="")
    company: Mapped[str] = mapped_column(Text, default="")
    position_tag: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="application_profiles")
    interview_records: Mapped[list[InterviewRecord]] = relationship(back_populates="application_profile")


class RagRetrievalLog(Base):
    __tablename__ = "rag_retrieval_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    interview_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_type: Mapped[str] = mapped_column(String(50), index=True)
    query_text: Mapped[str] = mapped_column(Text, default="")
    retriever_name: Mapped[str] = mapped_column(String(100), index=True)
    retrieval_mode: Mapped[str] = mapped_column(String(50), default="keyword")
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    hits_json: Mapped[str] = mapped_column(Text, default="[]")
    used_in_prompt: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped[User] = relationship(back_populates="rag_retrieval_logs")


class AgentDecisionLog(Base):
    __tablename__ = "agent_decision_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_type: Mapped[str] = mapped_column(String(50), index=True)
    next_action: Mapped[str] = mapped_column(String(50), index=True)
    stage: Mapped[str] = mapped_column(String(100), default="")
    difficulty: Mapped[str] = mapped_column(String(50), default="")
    focus: Mapped[str] = mapped_column(String(200), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    tools_json: Mapped[str] = mapped_column(Text, default="[]")
    state_json: Mapped[str] = mapped_column(Text, default="{}")
    decision_json: Mapped[str] = mapped_column(Text, default="{}")
    fallback_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped[User] = relationship(back_populates="agent_decision_logs")


class LangGraphCheckpointSummary(Base):
    __tablename__ = "langgraph_checkpoint_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[str] = mapped_column(String(200), index=True)
    runtime: Mapped[str] = mapped_column(String(50), default="langgraph", index=True)
    status: Mapped[str] = mapped_column(String(50), default="completed", index=True)
    current_node: Mapped[str] = mapped_column(String(100), default="")
    round_count: Mapped[int] = mapped_column(Integer, default=0)
    last_action: Mapped[str] = mapped_column(String(80), default="")
    last_question: Mapped[str] = mapped_column(Text, default="")
    requires_human_review: Mapped[int] = mapped_column(Integer, default=0)
    interrupt_json: Mapped[str] = mapped_column(Text, default="")
    resume_decision: Mapped[str] = mapped_column(Text, default="")
    runtime_trace_json: Mapped[str] = mapped_column(Text, default="[]")
    quality_gate_json: Mapped[str] = mapped_column(Text, default="{}")
    comparison_json: Mapped[str] = mapped_column(Text, default="{}")
    raw_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    knowledge_base: Mapped[str] = mapped_column(String(50), index=True)
    source_type: Mapped[str] = mapped_column(String(50), default="manual")
    status: Mapped[str] = mapped_column(String(40), default="enabled", index=True)
    visibility: Mapped[str] = mapped_column(String(40), default="private", index=True)
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="rag_documents")
    chunks: Mapped[list["RagChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("rag_documents.id"), index=True)
    knowledge_base: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    chunk_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    is_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    embedding_json: Mapped[str] = mapped_column(Text, default="[]")
    embedding_model: Mapped[str] = mapped_column(String(100), default="")
    embedding_status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user: Mapped[User] = relationship(back_populates="rag_chunks")
    document: Mapped[RagDocument] = relationship(back_populates="chunks")


class RagIngestionTask(Base):
    __tablename__ = "rag_ingestion_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("rag_documents.id"), nullable=True, index=True)
    knowledge_base: Mapped[str] = mapped_column(String(50), default="", index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    source_extension: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(255), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    can_retry: Mapped[int] = mapped_column(Integer, default=0, index=True)
    preview_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user: Mapped[User] = relationship(back_populates="rag_ingestion_tasks")


class TrainingTask(Base):
    __tablename__ = "training_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("application_profiles.id"),
        nullable=True,
        index=True,
    )
    source_interview_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("interview_records.id"),
        nullable=True,
        index=True,
    )
    weak_tag: Mapped[str] = mapped_column(String(80), index=True)
    weak_label: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="todo", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="medium", index=True)
    mastery_score: Mapped[int] = mapped_column(Integer, default=40)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="training_tasks")
