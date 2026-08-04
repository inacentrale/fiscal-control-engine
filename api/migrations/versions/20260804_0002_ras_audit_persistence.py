"""RAS audit persistence

Revision ID: 20260804_0002
Revises: 20260730_0001
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260804_0002"
down_revision: str | None = "20260730_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ras_audit_runs",
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("parent_audit_id", sa.String(length=64), nullable=True),
        sa.Column("agent_run_id", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("file_id", sa.String(length=64), nullable=True),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "reference_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "fact_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.run_id"]),
        sa.ForeignKeyConstraint(["file_id"], ["agent_files.file_id"]),
        sa.ForeignKeyConstraint(["parent_audit_id"], ["ras_audit_runs.audit_id"]),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.session_id"]),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_ras_audit_runs_file_id", "ras_audit_runs", ["file_id"])
    op.create_index(
        "ix_ras_audit_runs_agent_run_id",
        "ras_audit_runs",
        ["agent_run_id"],
    )
    op.create_index(
        "ix_ras_audit_runs_parent_audit_id",
        "ras_audit_runs",
        ["parent_audit_id"],
    )
    op.create_index("ix_ras_audit_runs_session_id", "ras_audit_runs", ["session_id"])
    op.create_table(
        "ras_audit_cases",
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("certainty", sa.String(length=40), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_id"], ["ras_audit_runs.audit_id"]),
        sa.PrimaryKeyConstraint("case_id"),
        sa.UniqueConstraint("audit_id", "candidate_id", name="uq_ras_audit_candidate"),
    )
    op.create_index("ix_ras_audit_cases_audit_id", "ras_audit_cases", ["audit_id"])
    op.create_table(
        "ras_audit_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_id"], ["ras_audit_runs.audit_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("audit_id", "sequence", name="uq_ras_audit_event_sequence"),
    )
    op.create_index("ix_ras_audit_events_audit_id", "ras_audit_events", ["audit_id"])


def downgrade() -> None:
    op.drop_index("ix_ras_audit_events_audit_id", table_name="ras_audit_events")
    op.drop_table("ras_audit_events")
    op.drop_index("ix_ras_audit_cases_audit_id", table_name="ras_audit_cases")
    op.drop_table("ras_audit_cases")
    op.drop_index("ix_ras_audit_runs_session_id", table_name="ras_audit_runs")
    op.drop_index("ix_ras_audit_runs_agent_run_id", table_name="ras_audit_runs")
    op.drop_index("ix_ras_audit_runs_parent_audit_id", table_name="ras_audit_runs")
    op.drop_index("ix_ras_audit_runs_file_id", table_name="ras_audit_runs")
    op.drop_table("ras_audit_runs")
