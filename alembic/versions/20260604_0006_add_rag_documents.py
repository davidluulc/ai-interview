"""add rag documents and chunks

Revision ID: 20260604_0006
Revises: 20260604_0005
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_0006"
down_revision: str | None = "20260604_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rag_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("knowledge_base", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rag_documents_id"), "rag_documents", ["id"], unique=False)
    op.create_index(op.f("ix_rag_documents_user_id"), "rag_documents", ["user_id"], unique=False)
    op.create_index(op.f("ix_rag_documents_knowledge_base"), "rag_documents", ["knowledge_base"], unique=False)

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("keywords_json", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["rag_documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rag_chunks_id"), "rag_chunks", ["id"], unique=False)
    op.create_index(op.f("ix_rag_chunks_user_id"), "rag_chunks", ["user_id"], unique=False)
    op.create_index(op.f("ix_rag_chunks_document_id"), "rag_chunks", ["document_id"], unique=False)
    op.create_index(op.f("ix_rag_chunks_knowledge_base"), "rag_chunks", ["knowledge_base"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_chunks_knowledge_base"), table_name="rag_chunks")
    op.drop_index(op.f("ix_rag_chunks_document_id"), table_name="rag_chunks")
    op.drop_index(op.f("ix_rag_chunks_user_id"), table_name="rag_chunks")
    op.drop_index(op.f("ix_rag_chunks_id"), table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_index(op.f("ix_rag_documents_knowledge_base"), table_name="rag_documents")
    op.drop_index(op.f("ix_rag_documents_user_id"), table_name="rag_documents")
    op.drop_index(op.f("ix_rag_documents_id"), table_name="rag_documents")
    op.drop_table("rag_documents")
