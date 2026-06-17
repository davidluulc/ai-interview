"""add langgraph checkpoint summaries

Revision ID: 20260614_0001
Revises: 20260606_0008
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260614_0001"
down_revision = "20260606_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "langgraph_checkpoint_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=200), nullable=False),
        sa.Column("runtime", sa.String(length=50), nullable=False, server_default="langgraph"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="completed"),
        sa.Column("current_node", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("round_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_action", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("last_question", sa.Text(), nullable=False, server_default=""),
        sa.Column("requires_human_review", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interrupt_json", sa.Text(), nullable=False, server_default=""),
        sa.Column("resume_decision", sa.Text(), nullable=False, server_default=""),
        sa.Column("runtime_trace_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("quality_gate_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("comparison_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("raw_summary_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_langgraph_checkpoint_summaries_id"), "langgraph_checkpoint_summaries", ["id"], unique=False)
    op.create_index(
        op.f("ix_langgraph_checkpoint_summaries_thread_id"),
        "langgraph_checkpoint_summaries",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_langgraph_checkpoint_summaries_runtime"),
        "langgraph_checkpoint_summaries",
        ["runtime"],
        unique=False,
    )
    op.create_index(
        op.f("ix_langgraph_checkpoint_summaries_status"),
        "langgraph_checkpoint_summaries",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_langgraph_checkpoint_summaries_status"), table_name="langgraph_checkpoint_summaries")
    op.drop_index(op.f("ix_langgraph_checkpoint_summaries_runtime"), table_name="langgraph_checkpoint_summaries")
    op.drop_index(op.f("ix_langgraph_checkpoint_summaries_thread_id"), table_name="langgraph_checkpoint_summaries")
    op.drop_index(op.f("ix_langgraph_checkpoint_summaries_id"), table_name="langgraph_checkpoint_summaries")
    op.drop_table("langgraph_checkpoint_summaries")
