from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class AgentSessionModel(Base):
    __tablename__ = "agent_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    active_file_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )


class AgentFileModel(Base):
    __tablename__ = "agent_files"

    file_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_sessions.session_id"),
        index=True,
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sheet_names: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    validated_for_agent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    anonymized_for_rag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rag_indexable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("agent_sessions.session_id"),
        nullable=True,
        index=True,
    )
    file_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("agent_files.file_id"),
        nullable=True,
        index=True,
    )
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class AgentMessageModel(Base):
    __tablename__ = "agent_messages"

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_runs.run_id"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class AgentRunEventModel(Base):
    __tablename__ = "agent_run_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_runs.run_id"),
        index=True,
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class AgentToolResultModel(Base):
    __tablename__ = "agent_tool_results"

    tool_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_runs.run_id"),
        index=True,
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    output: Mapped[dict[str, object]] = mapped_column(JsonType, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class RasAuditRunModel(Base):
    __tablename__ = "ras_audit_runs"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_audit_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("ras_audit_runs.audit_id"),
        nullable=True,
        index=True,
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("agent_runs.run_id"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("agent_sessions.session_id"),
        nullable=True,
        index=True,
    )
    file_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("agent_files.file_id"),
        nullable=True,
        index=True,
    )
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_versions: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
    fact_context: Mapped[dict[str, object]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class RasAuditCaseModel(Base):
    __tablename__ = "ras_audit_cases"
    __table_args__ = (
        UniqueConstraint("audit_id", "candidate_id", name="uq_ras_audit_candidate"),
    )

    case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audit_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ras_audit_runs.audit_id"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    certainty: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class RasAuditEventModel(Base):
    __tablename__ = "ras_audit_events"
    __table_args__ = (
        UniqueConstraint("audit_id", "sequence", name="uq_ras_audit_event_sequence"),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audit_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ras_audit_runs.audit_id"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JsonType,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class RasAuditCandidateJobModel(Base):
    __tablename__ = "ras_audit_candidate_jobs"
    __table_args__ = (
        UniqueConstraint(
            "audit_id",
            "candidate_id",
            "input_digest",
            name="uq_ras_candidate_job_input",
        ),
    )

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audit_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("ras_audit_runs.audit_id"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_audit_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
