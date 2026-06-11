"""add rag chunk embeddings

Revision ID: 20260606_0007
Revises: 20260604_0006
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260606_0007"
down_revision: str | None = "20260604_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rag_chunks", sa.Column("embedding_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("rag_chunks", sa.Column("embedding_model", sa.String(length=100), nullable=False, server_default=""))
    op.add_column(
        "rag_chunks",
        sa.Column("embedding_status", sa.String(length=50), nullable=False, server_default="pending"),
    )


def downgrade() -> None:
    op.drop_column("rag_chunks", "embedding_status")
    op.drop_column("rag_chunks", "embedding_model")
    op.drop_column("rag_chunks", "embedding_json")
