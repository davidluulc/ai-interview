"""add agent decision logs

Revision ID: 20260606_0008
Revises: 20260606_0007
Create Date: 2026-06-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260606_0008"
down_revision: str | None = "20260606_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_decision_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("application_profile_id", sa.Integer(), nullable=True),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("next_action", sa.String(length=50), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("difficulty", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("focus", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("tools_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("decision_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("fallback_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_decision_logs_id"), "agent_decision_logs", ["id"], unique=False)
    op.create_index(op.f("ix_agent_decision_logs_user_id"), "agent_decision_logs", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_agent_decision_logs_application_profile_id"),
        "agent_decision_logs",
        ["application_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_decision_logs_request_type"),
        "agent_decision_logs",
        ["request_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_decision_logs_next_action"),
        "agent_decision_logs",
        ["next_action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_decision_logs_next_action"), table_name="agent_decision_logs")
    op.drop_index(op.f("ix_agent_decision_logs_request_type"), table_name="agent_decision_logs")
    op.drop_index(op.f("ix_agent_decision_logs_application_profile_id"), table_name="agent_decision_logs")
    op.drop_index(op.f("ix_agent_decision_logs_user_id"), table_name="agent_decision_logs")
    op.drop_index(op.f("ix_agent_decision_logs_id"), table_name="agent_decision_logs")
    op.drop_table("agent_decision_logs")
