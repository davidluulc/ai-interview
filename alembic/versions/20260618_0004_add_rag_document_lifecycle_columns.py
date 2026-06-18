"""add rag document lifecycle columns

Revision ID: 20260618_0004
Revises: 20260618_0003
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0004"
down_revision = "20260618_0003"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, str(column.name)):
        op.add_column(table_name, column)


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=False)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    _add_column_if_missing(
        "rag_documents",
        sa.Column("status", sa.String(length=40), nullable=False, server_default="enabled"),
    )
    _add_column_if_missing(
        "rag_documents",
        sa.Column("visibility", sa.String(length=40), nullable=False, server_default="private"),
    )
    _add_column_if_missing(
        "rag_documents",
        sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "rag_documents",
        sa.Column("duplicate_chunk_count", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column_if_missing(
        "rag_chunks",
        sa.Column("chunk_hash", sa.String(length=64), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "rag_chunks",
        sa.Column("is_duplicate", sa.Integer(), nullable=False, server_default="0"),
    )

    _create_index_if_missing("rag_documents", "ix_rag_documents_status", ["status"])
    _create_index_if_missing("rag_documents", "ix_rag_documents_visibility", ["visibility"])
    _create_index_if_missing("rag_documents", "ix_rag_documents_content_hash", ["content_hash"])
    _create_index_if_missing("rag_chunks", "ix_rag_chunks_chunk_hash", ["chunk_hash"])
    _create_index_if_missing("rag_chunks", "ix_rag_chunks_is_duplicate", ["is_duplicate"])


def downgrade() -> None:
    _drop_index_if_exists("rag_chunks", "ix_rag_chunks_is_duplicate")
    _drop_index_if_exists("rag_chunks", "ix_rag_chunks_chunk_hash")
    _drop_index_if_exists("rag_documents", "ix_rag_documents_content_hash")
    _drop_index_if_exists("rag_documents", "ix_rag_documents_visibility")
    _drop_index_if_exists("rag_documents", "ix_rag_documents_status")

    _drop_column_if_exists("rag_chunks", "is_duplicate")
    _drop_column_if_exists("rag_chunks", "chunk_hash")
    _drop_column_if_exists("rag_documents", "duplicate_chunk_count")
    _drop_column_if_exists("rag_documents", "content_hash")
    _drop_column_if_exists("rag_documents", "visibility")
    _drop_column_if_exists("rag_documents", "status")
