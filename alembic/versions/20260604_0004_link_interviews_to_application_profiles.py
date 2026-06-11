"""link interviews to application profiles

Revision ID: 20260604_0004
Revises: 20260604_0003
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260604_0004"
down_revision: str | None = "20260604_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("interview_records", sa.Column("application_profile_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_interview_records_application_profile_id"),
        "interview_records",
        ["application_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_interview_records_application_profile_id"), table_name="interview_records")
    op.drop_column("interview_records", "application_profile_id")
