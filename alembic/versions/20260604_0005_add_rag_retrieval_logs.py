"""add rag retrieval logs

Revision ID: 20260604_0005
Revises: 20260604_0004
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_0005"
down_revision: str | None = "20260604_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rag_retrieval_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("application_profile_id", sa.Integer(), nullable=True),
        sa.Column("interview_record_id", sa.Integer(), nullable=True),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("retriever_name", sa.String(length=100), nullable=False),
        sa.Column("retrieval_mode", sa.String(length=50), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False),
        sa.Column("hits_json", sa.Text(), nullable=False),
        sa.Column("used_in_prompt", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rag_retrieval_logs_id"), "rag_retrieval_logs", ["id"], unique=False)
    op.create_index(op.f("ix_rag_retrieval_logs_user_id"), "rag_retrieval_logs", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_rag_retrieval_logs_application_profile_id"),
        "rag_retrieval_logs",
        ["application_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_retrieval_logs_interview_record_id"),
        "rag_retrieval_logs",
        ["interview_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_retrieval_logs_request_type"),
        "rag_retrieval_logs",
        ["request_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_retrieval_logs_retriever_name"),
        "rag_retrieval_logs",
        ["retriever_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_retrieval_logs_retriever_name"), table_name="rag_retrieval_logs")
    op.drop_index(op.f("ix_rag_retrieval_logs_request_type"), table_name="rag_retrieval_logs")
    op.drop_index(op.f("ix_rag_retrieval_logs_interview_record_id"), table_name="rag_retrieval_logs")
    op.drop_index(op.f("ix_rag_retrieval_logs_application_profile_id"), table_name="rag_retrieval_logs")
    op.drop_index(op.f("ix_rag_retrieval_logs_user_id"), table_name="rag_retrieval_logs")
    op.drop_index(op.f("ix_rag_retrieval_logs_id"), table_name="rag_retrieval_logs")
    op.drop_table("rag_retrieval_logs")
