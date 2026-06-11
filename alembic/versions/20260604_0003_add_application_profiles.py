"""add application profiles

Revision ID: 20260604_0003
Revises: 20260603_0002
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_0003"
down_revision: str | None = "20260603_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("target_role", sa.String(length=200), nullable=False),
        sa.Column("application_type", sa.String(length=100), nullable=False),
        sa.Column("resume", sa.Text(), nullable=False),
        sa.Column("jd", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("position_tag", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_application_profiles_id"), "application_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_application_profiles_user_id"), "application_profiles", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_application_profiles_user_id"), table_name="application_profiles")
    op.drop_index(op.f("ix_application_profiles_id"), table_name="application_profiles")
    op.drop_table("application_profiles")
