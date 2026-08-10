from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AgentRunHttpRequest(BaseModel):
    message: str = Field(min_length=1)
    file_path: str | None = None
    session_id: str | None = None
    file_id: str | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    requested_tool: str | None = None
    sheet_name: str | None = None

    @model_validator(mode="after")
    def validate_file_reference(self) -> "AgentRunHttpRequest":
        has_direct_path = self.file_path is not None
        has_session_reference = self.session_id is not None or self.file_id is not None
        if has_direct_path and has_session_reference:
            raise ValueError("choose either file_path or session_id/file_id")
        if has_session_reference and not (self.session_id and self.file_id):
            raise ValueError("session_id and file_id are required together")
        return self


class AgentToolResultResponse(BaseModel):
    tool_name: str
    ok: bool
    output: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None


class AgentRunEventResponse(BaseModel):
    event_type: str
    title: str
    message: str
    status: str
    tool_name: str | None = None
    provider_name: str | None = None
    model_name: str | None = None


class AgentRunResponse(BaseModel):
    answer: str
    provider_name: str
    model_name: str
    execution_events: list[AgentRunEventResponse]
    tool_results: list[AgentToolResultResponse]


class AgentFileUploadResponse(BaseModel):
    session_id: str
    file_id: str
    original_filename: str
    expires_at: datetime
    validated_for_agent: bool
    rag_indexable: bool
    sheet_names: list[str]


class AgentConversationSummaryResponse(BaseModel):
    run_id: str
    session_id: str | None
    file_id: str | None
    title: str
    status: str
    created_at: datetime


class AgentConversationListResponse(BaseModel):
    items: list[AgentConversationSummaryResponse]


class AgentConversationMessageResponse(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: datetime


class AgentConversationDetailResponse(BaseModel):
    run_id: str
    session_id: str | None
    file_id: str | None
    messages: list[AgentConversationMessageResponse]


class AgentFileSummaryResponse(BaseModel):
    session_id: str
    file_id: str
    original_filename: str
    file_size_bytes: int | None
    sheet_names: list[str]
    created_at: datetime
    expires_at: datetime
    status: str


class AgentFileListResponse(BaseModel):
    items: list[AgentFileSummaryResponse]


class AgentDashboardChartResponse(BaseModel):
    chart_id: str
    title: str
    kind: str
    metric: str
    labels: list[str]
    values: list[float | int]
    series: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentFileDashboardResponse(BaseModel):
    file_id: str
    sheet_name: str
    summary: dict[str, Any]
    schema_overview: dict[str, Any]
    metrics: dict[str, Any]
    amount_metrics_by_currency: dict[str, dict[str, float | int]] = Field(
        default_factory=dict,
    )
    charts: list[AgentDashboardChartResponse]
    quality: dict[str, Any]


class AgentSessionContextEventResponse(BaseModel):
    event_type: str
    title: str
    message: str
    status: str
    tool_name: str | None = None
    provider_name: str | None = None
    model_name: str | None = None
    created_at: datetime


class AgentSessionContextResponse(BaseModel):
    state: str
    session_id: str
    active_file: AgentFileSummaryResponse | None
    files: list[AgentFileSummaryResponse]
    dashboard: AgentFileDashboardResponse | None
    last_agent_events: list[AgentSessionContextEventResponse]


class RasWorkflowCaseResponse(BaseModel):
    candidate_id: str
    state: str
    status: str
    missing_facts: list[str]


class RasWorkflowStatusResponse(BaseModel):
    audit_id: str
    parent_audit_id: str | None
    status: str
    total_candidates: int
    page: int
    page_size: int
    report_available: bool
    cases: list[RasWorkflowCaseResponse]


class RasCandidateAssessmentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    session_id: str = Field(min_length=1)
    file_id: str = Field(min_length=1)
    sheet_name: str = Field(min_length=1)


class RasCandidateJobRequest(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4_000)


class RasCandidateJobBatchRequest(BaseModel):
    audit_id: str = Field(min_length=1, max_length=64)
    session_id: str = Field(min_length=1, max_length=64)
    file_id: str = Field(min_length=1, max_length=64)
    sheet_name: str = Field(min_length=1, max_length=128)
    candidates: list[RasCandidateJobRequest] = Field(min_length=1, max_length=100)
    max_concurrency: int = Field(default=2, ge=1, le=4)


class RasCandidateJobResponse(BaseModel):
    job_id: str
    audit_id: str
    candidate_id: str
    state: str
    attempt_count: int
    result_audit_id: str | None = None
    error_code: str | None = None


class RasCandidateJobBatchResponse(BaseModel):
    jobs: list[RasCandidateJobResponse]
    result_audit_id: str | None = None


class AgentErrorDetail(BaseModel):
    code: str
    message: str


class AgentErrorResponse(BaseModel):
    error: AgentErrorDetail
