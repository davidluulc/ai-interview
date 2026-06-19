"""add application profile status

Revision ID: 20260619_0001
Revises: 20260618_0004
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260619_0001"
down_revision = "20260618_0004"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _column_exists("application_profiles", "status"):
        op.add_column(
            "application_profiles",
            sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        )
    if not _index_exists("application_profiles", "ix_application_profiles_status"):
        op.create_index("ix_application_profiles_status", "application_profiles", ["status"], unique=False)


def downgrade() -> None:
    if _index_exists("application_profiles", "ix_application_profiles_status"):
        op.drop_index("ix_application_profiles_status", table_name="application_profiles")
    if _column_exists("application_profiles", "status"):
        op.drop_column("application_profiles", "status")
