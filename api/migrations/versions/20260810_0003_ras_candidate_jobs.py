"""RAS candidate jobs

Revision ID: 20260810_0003
Revises: 20260804_0002
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0003"
down_revision: str | None = "20260804_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ras_audit_candidate_jobs",
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("input_digest", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("result_audit_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_id"], ["ras_audit_runs.audit_id"]),
        sa.PrimaryKeyConstraint("job_id"),
        sa.UniqueConstraint(
            "audit_id",
            "candidate_id",
            "input_digest",
            name="uq_ras_candidate_job_input",
        ),
    )
    op.create_index(
        "ix_ras_audit_candidate_jobs_audit_id",
        "ras_audit_candidate_jobs",
        ["audit_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ras_audit_candidate_jobs_audit_id",
        table_name="ras_audit_candidate_jobs",
    )
    op.drop_table("ras_audit_candidate_jobs")
