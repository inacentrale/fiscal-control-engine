"""agent persistence

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("active_file_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(
        "ix_agent_sessions_active_file_id",
        "agent_sessions",
        ["active_file_id"],
    )
    op.create_table(
        "agent_files",
        sa.Column("file_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("sheet_names", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_for_agent", sa.Boolean(), nullable=False),
        sa.Column("anonymized_for_rag", sa.Boolean(), nullable=False),
        sa.Column("rag_indexable", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.session_id"]),
        sa.PrimaryKeyConstraint("file_id"),
    )
    op.create_index("ix_agent_files_session_id", "agent_files", ["session_id"])
    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("file_id", sa.String(length=64), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["agent_files.file_id"]),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.session_id"]),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_agent_runs_file_id", "agent_runs", ["file_id"])
    op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"])
    op.create_table(
        "agent_messages",
        sa.Column("message_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"]),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_index("ix_agent_messages_run_id", "agent_messages", ["run_id"])
    op.create_table(
        "agent_run_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=True),
        sa.Column("provider_name", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_agent_run_events_run_id", "agent_run_events", ["run_id"])
    op.create_table(
        "agent_tool_results",
        sa.Column("tool_result_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"]),
        sa.PrimaryKeyConstraint("tool_result_id"),
    )
    op.create_index("ix_agent_tool_results_run_id", "agent_tool_results", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_tool_results_run_id", table_name="agent_tool_results")
    op.drop_table("agent_tool_results")
    op.drop_index("ix_agent_run_events_run_id", table_name="agent_run_events")
    op.drop_table("agent_run_events")
    op.drop_index("ix_agent_messages_run_id", table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_index("ix_agent_runs_session_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_file_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_agent_files_session_id", table_name="agent_files")
    op.drop_table("agent_files")
    op.drop_index("ix_agent_sessions_active_file_id", table_name="agent_sessions")
    op.drop_table("agent_sessions")
