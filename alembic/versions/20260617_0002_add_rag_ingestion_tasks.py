"""add rag ingestion tasks

Revision ID: 20260617_0002
Revises: 20260614_0001
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260617_0002"
down_revision = "20260614_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_ingestion_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("knowledge_base", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("original_filename", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("source_extension", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("can_retry", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("preview_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("input_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["rag_documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rag_ingestion_tasks_id"), "rag_ingestion_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_task_id"), "rag_ingestion_tasks", ["task_id"], unique=True)
    op.create_index(op.f("ix_rag_ingestion_tasks_user_id"), "rag_ingestion_tasks", ["user_id"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_document_id"), "rag_ingestion_tasks", ["document_id"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_status"), "rag_ingestion_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_rag_ingestion_tasks_can_retry"), "rag_ingestion_tasks", ["can_retry"], unique=False)
    op.create_index(
        op.f("ix_rag_ingestion_tasks_knowledge_base"),
        "rag_ingestion_tasks",
        ["knowledge_base"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_ingestion_tasks_knowledge_base"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_can_retry"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_status"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_document_id"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_user_id"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_task_id"), table_name="rag_ingestion_tasks")
    op.drop_index(op.f("ix_rag_ingestion_tasks_id"), table_name="rag_ingestion_tasks")
    op.drop_table("rag_ingestion_tasks")
