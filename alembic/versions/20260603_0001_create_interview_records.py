"""create interview records table

Revision ID: 20260603_0001
Revises:
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260603_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interview_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_name", sa.String(length=100), nullable=False),
        sa.Column("target_role", sa.String(length=200), nullable=False),
        sa.Column("application_type", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=100), nullable=False),
        sa.Column("depth", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("profile_json", sa.Text(), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_records_id"), "interview_records", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_interview_records_id"), table_name="interview_records")
    op.drop_table("interview_records")
