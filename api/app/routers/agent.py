import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from queue import Queue
from tempfile import NamedTemporaryFile
from threading import Thread
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.agent.dashboard_service import build_file_dashboard, create_excel_tool_executor
from app.agent.orchestrator import (
    AgentOrchestrator,
    AgentRunEvent,
    AgentRunRequest,
    AgentRunResult,
)
from app.agent_file.domain import (
    AgentFileExpiredError,
    AgentFileMissingError,
    AgentFileReadError,
    AgentFileTooLargeError,
    UnsupportedAgentFileError,
)
from app.agent_file.file_resolver import AgentFileResolver
from app.agent_file.persistent_file_store import PersistentAgentFileStore
from app.agent_file.temporary_file_store import TemporaryAgentFileStore
from app.agent_file.upload_service import AgentFileUploadService
from app.agent_file.upload_validator import AgentExcelUploadValidator
from app.agent_persistence.repository import (
    AgentFileSummary,
    AgentRunEventSummary,
    SqlAlchemyAgentRepository,
)
from app.config import Settings, get_settings
from app.database import Base, create_database_engine, create_session_factory
from app.llm.domain import ToolCall
from app.llm.model_provider_factory import create_model_provider
from app.ras_audit.audit_derivation import RasAuditDerivationService
from app.ras_audit.audit_report import (
    RAS_REPORT_CONTRACT_VERSION,
    RasAuditReport,
    RasAuditReportGenerator,
    ras_report_business_payload,
)
from app.ras_audit.fact_context import (
    RasExplicitFactExtractor,
    RasFactContextAttestor,
    RasFactExtraction,
    load_ras_user_fact_patterns,
)
from app.ras_audit.jobs import (
    RasCandidateJob,
    RasCandidateJobRepository,
    run_candidate_jobs,
)
from app.ras_audit.persisted_report import (
    PersistedRasAuditReportError,
    PersistedRasAuditReportService,
)
from app.ras_audit.persistence import SqlAlchemyRasAuditRepository
from app.ras_audit.report_exports import (
    RAS_REPORT_EXPORT_MAX_BYTES,
    render_ras_report_pdf,
    render_ras_report_xlsx,
)
from app.ras_audit.workflow import (
    RasAuditWorkflowService,
    RasWorkflowStatusError,
)
from app.schemas.agent import (
    AgentConversationDetailResponse,
    AgentConversationListResponse,
    AgentConversationMessageResponse,
    AgentConversationSummaryResponse,
    AgentErrorDetail,
    AgentErrorResponse,
    AgentFileListResponse,
    AgentFileSummaryResponse,
    AgentFileUploadResponse,
    AgentRunEventResponse,
    AgentRunHttpRequest,
    AgentRunResponse,
    AgentSessionContextEventResponse,
    AgentSessionContextResponse,
    AgentToolResultResponse,
    RasCandidateAssessmentRequest,
    RasCandidateJobBatchRequest,
    RasCandidateJobBatchResponse,
    RasCandidateJobResponse,
    RasWorkflowCaseResponse,
    RasWorkflowStatusResponse,
)

DEFAULT_AGENT_TOOLS = (
    "list_sheets",
    "get_columns",
    "profile_sheet",
    "classify_ledger_schema",
    "analyze_ledger",
    "aggregate_ledger",
    "aggregate_business_nature",
    "query_ledger_entries",
    "calculate_ledger_metrics",
    "detect_data_quality_issues",
    "detect_tax_candidates",
    "reconstruct_accounting_entry",
    "detect_ras_candidates",
    "query_tax_rag",
)
ATTESTED_LEGAL_AGENT_TOOLS = (
    "resolve_applicable_ras_rule",
    "calculate_theoretical_ras",
)
MAPPED_RAS_AUDIT_AGENT_TOOLS = (
    "find_ras_counterpart",
)
ATTESTED_PERSISTED_RAS_AGENT_TOOLS = ("generate_ras_audit_report",)
FULLY_ATTESTED_RAS_AGENT_TOOLS = (
    "run_ras_audit_batch",
    "assess_ras_accounting",
)

router = APIRouter(prefix="/agent", tags=["agent"])


async def get_api_settings() -> Settings:
    return get_settings()


SettingsDependency = Annotated[Settings, Depends(get_api_settings)]


class AgentEndpointError(RuntimeError):
    def __init__(self, public_code: str, public_message: str) -> None:
        self.public_code = public_code
        self.public_message = public_message
        super().__init__(public_code)


async def get_agent_orchestrator(settings: SettingsDependency) -> AgentOrchestrator:
    try:
        model_provider = create_model_provider(
            provider_chain=settings.llm_provider_chain,
            openai_compatible_api_key=(
                settings.llm_openai_compatible_api_key.get_secret_value()
                if settings.llm_openai_compatible_api_key is not None
                else None
            ),
            openai_compatible_base_url=settings.llm_openai_compatible_base_url,
            gemini_api_key=(
                settings.llm_gemini_api_key.get_secret_value()
                if settings.llm_gemini_api_key is not None
                else None
            ),
            gemini_base_url=settings.llm_gemini_base_url,
            groq_api_key=(
                settings.llm_groq_api_key.get_secret_value()
                if settings.llm_groq_api_key is not None
                else None
            ),
            groq_base_url=settings.llm_groq_base_url,
        )
        return AgentOrchestrator(
            model_provider=model_provider,
            tool_executor=create_excel_tool_executor(
                settings,
                ras_audit_repository=(
                    _get_ras_audit_repository(settings.database_url)
                    if settings.database_url
                    else None
                ),
            ),
            max_answer_characters=settings.agent_max_answer_characters,
            ras_fact_extractor=(
                RasExplicitFactExtractor(
                    load_ras_user_fact_patterns(
                        Path(settings.ras_user_fact_patterns_path)
                    )
                )
                if settings.ras_fact_context_signing_key is not None
                else None
            ),
            ras_fact_attestor=(
                RasFactContextAttestor(
                    settings.ras_fact_context_signing_key.get_secret_value()
                )
                if settings.ras_fact_context_signing_key is not None
                else None
            ),
        )
    except ValueError as exc:
        raise AgentEndpointError(
            public_code="agent_configuration_error",
            public_message="La configuration agent est invalide.",
        ) from exc


@lru_cache
def _get_agent_repository(database_url: str) -> SqlAlchemyAgentRepository:
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    return SqlAlchemyAgentRepository(session_factory=create_session_factory(engine))


@lru_cache
def _get_ras_audit_repository(database_url: str) -> SqlAlchemyRasAuditRepository:
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    return SqlAlchemyRasAuditRepository(session_factory=create_session_factory(engine))


@lru_cache
def _get_ras_candidate_job_repository(
    database_url: str,
) -> RasCandidateJobRepository:
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    return RasCandidateJobRepository(session_factory=create_session_factory(engine))


async def get_agent_repository(
    settings: SettingsDependency,
) -> SqlAlchemyAgentRepository | None:
    if not settings.database_url:
        return None
    return _get_agent_repository(settings.database_url)


AgentRepositoryDependency = Annotated[
    SqlAlchemyAgentRepository | None,
    Depends(get_agent_repository),
]


async def get_ras_audit_repository(
    settings: SettingsDependency,
) -> SqlAlchemyRasAuditRepository | None:
    if not settings.database_url:
        return None
    return _get_ras_audit_repository(settings.database_url)


RasAuditRepositoryDependency = Annotated[
    SqlAlchemyRasAuditRepository | None,
    Depends(get_ras_audit_repository),
]


async def get_ras_candidate_job_repository(
    settings: SettingsDependency,
) -> RasCandidateJobRepository | None:
    if not settings.database_url:
        return None
    return _get_ras_candidate_job_repository(settings.database_url)


RasCandidateJobRepositoryDependency = Annotated[
    RasCandidateJobRepository | None,
    Depends(get_ras_candidate_job_repository),
]


@lru_cache
def _get_agent_file_store(
    storage_root_path: str,
    ttl_seconds: int,
) -> TemporaryAgentFileStore:
    return TemporaryAgentFileStore(
        storage_root=Path(storage_root_path),
        ttl=timedelta(seconds=ttl_seconds),
    )


async def get_agent_file_store(settings: SettingsDependency) -> TemporaryAgentFileStore:
    return _get_agent_file_store(
        storage_root_path=settings.agent_file_storage_root_path,
        ttl_seconds=settings.agent_file_ttl_seconds,
    )


async def get_agent_file_resolver(
    settings: SettingsDependency,
    repository: AgentRepositoryDependency,
) -> AgentFileResolver:
    store = _build_agent_file_store(settings=settings, repository=repository)
    return AgentFileResolver(store=store)


async def get_agent_file_upload_service(
    settings: SettingsDependency,
    repository: AgentRepositoryDependency,
) -> AgentFileUploadService:
    validator = AgentExcelUploadValidator(
        max_file_size_bytes=settings.agent_file_max_upload_bytes,
    )
    return AgentFileUploadService(
        store=_build_agent_file_store(
            settings=settings,
            repository=repository,
            upload_validator=validator,
        ),
        validator=validator,
    )


AgentOrchestratorDependency = Annotated[
    AgentOrchestrator,
    Depends(get_agent_orchestrator),
]
AgentFileResolverDependency = Annotated[
    AgentFileResolver,
    Depends(get_agent_file_resolver),
]
AgentFileUploadServiceDependency = Annotated[
    AgentFileUploadService,
    Depends(get_agent_file_upload_service),
]
AgentListLimit = Annotated[int, Query(ge=1, le=50)]


async def _copy_upload_to_temporary_file(
    uploaded_file: UploadFile,
    max_upload_bytes: int,
) -> Path:
    source_suffix = Path(uploaded_file.filename or "").suffix
    with NamedTemporaryFile(
        prefix="agent-upload-",
        suffix=source_suffix,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
        written_bytes = 0
        while chunk := await uploaded_file.read(1024 * 1024):
            written_bytes += len(chunk)
            if written_bytes > max_upload_bytes:
                temporary_path.unlink(missing_ok=True)
                raise AgentFileTooLargeError("agent file is too large")
            temporary_file.write(chunk)
    return temporary_path


@router.post(
    "/files",
    response_model=AgentFileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": AgentErrorResponse},
        413: {"model": AgentErrorResponse},
    },
)
async def upload_agent_file(
    settings: SettingsDependency,
    upload_service: AgentFileUploadServiceDependency,
    file: Annotated[UploadFile, File()],
    session_id: str | None = Query(default=None, min_length=1),
) -> AgentFileUploadResponse | JSONResponse:
    temporary_path: Path | None = None
    try:
        temporary_path = await _copy_upload_to_temporary_file(
            uploaded_file=file,
            max_upload_bytes=settings.agent_file_max_upload_bytes,
        )
        result = upload_service.register_upload(
            source_path=temporary_path,
            original_filename=file.filename or "",
            session_id=session_id,
        )
    except AgentFileTooLargeError:
        return _to_error_response(
            AgentEndpointError(
                public_code="agent_file_too_large",
                public_message="Le fichier Excel agent depasse la taille autorisee.",
            ),
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    except UnsupportedAgentFileError:
        return _to_error_response(
            AgentEndpointError(
                public_code="agent_file_unsupported",
                public_message="Le format du fichier agent n'est pas supporte.",
            ),
        )
    except AgentFileReadError:
        return _to_error_response(
            AgentEndpointError(
                public_code="agent_file_invalid",
                public_message="Le fichier Excel agent est invalide ou illisible.",
            ),
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        await file.close()

    return AgentFileUploadResponse(
        session_id=result.session_id,
        file_id=result.file_id,
        original_filename=result.original_filename,
        expires_at=result.expires_at,
        validated_for_agent=result.validated_for_agent,
        rag_indexable=result.rag_indexable,
        sheet_names=list(result.sheet_names),
    )


@router.get(
    "/conversations",
    response_model=AgentConversationListResponse,
)
async def list_agent_conversations(
    repository: AgentRepositoryDependency,
    limit: AgentListLimit = 20,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> AgentConversationListResponse:
    if repository is None:
        return AgentConversationListResponse(items=[])
    return AgentConversationListResponse(
        items=[
            AgentConversationSummaryResponse(
                run_id=conversation.run_id,
                session_id=conversation.session_id,
                file_id=conversation.file_id,
                title=conversation.title,
                status=conversation.status,
                created_at=conversation.created_at,
            )
            for conversation in repository.list_recent_conversations(
                limit=limit,
                search=search,
            )
        ],
    )


@router.get(
    "/conversations/{run_id}",
    response_model=AgentConversationDetailResponse,
    responses={404: {"model": AgentErrorResponse}},
)
async def get_agent_conversation(
    run_id: str,
    repository: AgentRepositoryDependency,
) -> AgentConversationDetailResponse | JSONResponse:
    conversation = repository.get_conversation(run_id) if repository else None
    if conversation is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "agent_conversation_not_found",
                    "message": "La discussion demandée est introuvable.",
                },
            },
        )
    return AgentConversationDetailResponse(
        run_id=conversation.run_id,
        session_id=conversation.session_id,
        file_id=conversation.file_id,
        messages=[
            AgentConversationMessageResponse(
                message_id=message.message_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in conversation.messages
        ],
    )


@router.get(
    "/files",
    response_model=AgentFileListResponse,
)
async def list_agent_files(
    repository: AgentRepositoryDependency,
    limit: AgentListLimit = 20,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> AgentFileListResponse:
    if repository is None:
        return AgentFileListResponse(items=[])
    return AgentFileListResponse(
        items=[
            AgentFileSummaryResponse(
                session_id=file.session_id,
                file_id=file.file_id,
                original_filename=file.original_filename,
                file_size_bytes=file.file_size_bytes,
                sheet_names=list(file.sheet_names),
                created_at=file.created_at,
                expires_at=file.expires_at,
                status=file.status,
            )
            for file in repository.list_recent_files(limit=limit, search=search)
        ],
    )


@router.get(
    "/sessions/{session_id}/context",
    response_model=AgentSessionContextResponse,
)
async def get_agent_session_context(
    session_id: str,
    settings: SettingsDependency,
    repository: AgentRepositoryDependency,
) -> AgentSessionContextResponse | JSONResponse:
    if repository is None:
        return _empty_session_context(session_id)
    active_file = repository.get_active_file(session_id)
    session_files = repository.list_session_files(session_id)
    last_events = repository.list_recent_session_events(session_id)
    if active_file is None:
        return AgentSessionContextResponse(
            state="empty",
            session_id=session_id,
            active_file=None,
            files=[_to_agent_file_summary_response(file) for file in session_files],
            dashboard=None,
            last_agent_events=[
                _to_session_context_event_response(event) for event in last_events
            ],
        )
    try:
        stored_file = repository.find_file(
            session_id=active_file.session_id,
            file_id=active_file.file_id,
        )
        if stored_file is None:
            return _to_error_response(_file_missing_error())
        if stored_file.expires_at <= datetime.now(tz=UTC):
            return _to_error_response(_file_expired_error())
        if not stored_file.path.is_file():
            return _to_error_response(_file_missing_error())
        if not active_file.sheet_names:
            return _to_error_response(
                AgentEndpointError(
                    public_code="agent_file_invalid",
                    public_message="Le fichier Excel actif n'a aucune feuille lisible.",
                ),
            )
        dashboard = build_file_dashboard(
            settings=settings,
            file_id=active_file.file_id,
            file_path=stored_file.path,
            sheet_name=active_file.sheet_names[0],
        )
    except AgentFileExpiredError:
        return _to_error_response(_file_expired_error())
    except AgentFileMissingError:
        return _to_error_response(_file_missing_error())
    except ValueError:
        return _to_error_response(
            AgentEndpointError(
                public_code="agent_dashboard_unavailable",
                public_message="Le tableau de bord du fichier actif est indisponible.",
            ),
        )
    return AgentSessionContextResponse(
        state="ready",
        session_id=session_id,
        active_file=_to_agent_file_summary_response(active_file),
        files=[_to_agent_file_summary_response(file) for file in session_files],
        dashboard=dashboard,
        last_agent_events=[
            _to_session_context_event_response(event) for event in last_events
        ],
    )


def _ras_audit_report_response(
    report: RasAuditReport,
    audit_id: str,
    report_format: Literal["csv", "json", "xlsx", "pdf"],
    *,
    preview: bool = False,
) -> Response:
    generator = RasAuditReportGenerator()
    content: str | bytes
    safe_audit_id = "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in audit_id.strip()
    )
    if report_format == "json":
        content = (
            json.dumps(
                ras_report_business_payload(
                    report,
                    expose_document_references=True,
                ),
                ensure_ascii=False,
                default=str,
                sort_keys=True,
            )
            if preview
            else generator.to_json(report)
        )
        media_type = "application/json"
    elif report_format == "xlsx":
        content = render_ras_report_xlsx(report)
        media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    elif report_format == "pdf":
        content = render_ras_report_pdf(report)
        media_type = "application/pdf"
    else:
        content = generator.to_csv(report)
        media_type = "text/csv"
    filename = f"rapport-audit-ras-{safe_audit_id}.{report_format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Audit-ID": audit_id,
            "X-Report-Contract-Version": RAS_REPORT_CONTRACT_VERSION,
            "X-Report-Max-Bytes": str(RAS_REPORT_EXPORT_MAX_BYTES),
        },
    )


def _result_audit_id(result: AgentRunResult) -> str | None:
    for tool_result in reversed(result.tool_results):
        if not tool_result.ok or tool_result.output is None:
            continue
        audit_id = tool_result.output.get("audit_id")
        if isinstance(audit_id, str) and audit_id.strip():
            return audit_id
    return None


def _ras_candidate_job_response(job: RasCandidateJob) -> RasCandidateJobResponse:
    return RasCandidateJobResponse(
        job_id=job.job_id,
        audit_id=job.audit_id,
        candidate_id=job.candidate_id,
        state=job.state.value,
        attempt_count=job.attempt_count,
        result_audit_id=job.result_audit_id,
        error_code=job.error_code,
    )


@router.delete(
    "/conversations/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": AgentErrorResponse}},
)
async def delete_agent_conversation(
    run_id: str,
    repository: AgentRepositoryDependency,
) -> Response:
    deleted = repository.delete_conversation(run_id) if repository else False
    if not deleted:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/ras-audits/{audit_id}",
    response_model=RasWorkflowStatusResponse,
    responses={
        404: {"model": AgentErrorResponse},
        503: {"model": AgentErrorResponse},
    },
)
async def get_ras_audit_workflow_status(
    audit_id: str,
    repository: RasAuditRepositoryDependency,
    session_id: Annotated[str, Query(min_length=1)],
    file_id: Annotated[str, Query(min_length=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RasWorkflowStatusResponse | JSONResponse:
    if repository is None:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_audit_repository_unavailable",
                public_message="La persistance des audits RAS est indisponible.",
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        workflow = RasAuditWorkflowService(repository).status(
            audit_id=audit_id,
            session_id=session_id,
            file_id=file_id,
            page=page,
            page_size=page_size,
        )
    except RasWorkflowStatusError:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_audit_not_found",
                public_message="L'audit RAS demande est introuvable.",
            ),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return RasWorkflowStatusResponse(
        audit_id=workflow.audit_id,
        parent_audit_id=workflow.parent_audit_id,
        status=workflow.status,
        total_candidates=workflow.total_candidates,
        page=workflow.page,
        page_size=workflow.page_size,
        report_available=workflow.report_available,
        cases=[
            RasWorkflowCaseResponse(
                candidate_id=case.candidate_id,
                state=case.state.value,
                status=case.status,
                missing_facts=list(case.missing_facts),
            )
            for case in workflow.cases
        ],
    )


@router.post(
    "/ras-audits/{audit_id}/candidates/process",
    response_model=RasCandidateJobBatchResponse,
    responses={
        400: {"model": AgentErrorResponse},
        503: {"model": AgentErrorResponse},
    },
)
async def process_ras_audit_candidates(
    audit_id: str,
    request: RasCandidateJobBatchRequest,
    orchestrator: AgentOrchestratorDependency,
    file_resolver: AgentFileResolverDependency,
    job_repository: RasCandidateJobRepositoryDependency,
    audit_repository: RasAuditRepositoryDependency,
) -> RasCandidateJobBatchResponse | JSONResponse:
    if job_repository is None or audit_repository is None:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_job_repository_unavailable",
                public_message="La reprise des candidats RAS est indisponible.",
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if request.audit_id != audit_id or len(
        {candidate.candidate_id for candidate in request.candidates}
    ) != len(request.candidates):
        return _to_error_response(
            AgentEndpointError(
                public_code="invalid_ras_candidate_batch",
                public_message="Le lot de candidats RAS est invalide.",
            )
        )
    try:
        file_path = file_resolver.resolve_file_path(
            session_id=request.session_id,
            file_id=request.file_id,
            direct_file_path=None,
        )
        if file_path is None:
            return _to_error_response(_file_missing_error())
        messages = {
            candidate.candidate_id: candidate.message
            for candidate in request.candidates
        }
        jobs = tuple(
            job_repository.enqueue(
                audit_id=audit_id,
                candidate_id=candidate.candidate_id,
                session_id=request.session_id,
                file_id=request.file_id,
                input_token="\x1f".join(
                    (
                        request.session_id,
                        request.file_id,
                        request.sheet_name,
                        candidate.message,
                    )
                ),
            )
            for candidate in request.candidates
        )

        def worker(job: RasCandidateJob) -> None:
            claimed = job_repository.claim(job.job_id)
            if claimed is None:
                return
            try:
                result = orchestrator.run(
                    AgentRunRequest(
                        user_message=messages[job.candidate_id],
                        file_path=file_path,
                        sheet_name=request.sheet_name,
                        allowed_tools=(
                            "assess_ras_accounting",
                            "generate_ras_audit_report",
                        ),
                        direct_tool_call=ToolCall(
                            name="assess_ras_accounting",
                            arguments={
                                "base_audit_id": audit_id,
                                "candidate_id": job.candidate_id,
                            },
                        ),
                        session_id=request.session_id,
                        file_id=request.file_id,
                    )
                )
            except Exception:  # noqa: BLE001 - boundary sanitizes worker failures
                job_repository.fail(
                    job.job_id, error_code="ras_candidate_technical_failure"
                )
                return
            failure = next(
                (tool for tool in result.tool_results if not tool.ok), None
            )
            if failure is not None:
                job_repository.fail(
                    job.job_id,
                    error_code=failure.error_code or "ras_candidate_job_failed",
                )
                return
            result_audit_id = _result_audit_id(result)
            if result_audit_id is None:
                job_repository.fail(
                    job.job_id, error_code="ras_candidate_result_missing"
                )
                return
            job_repository.complete(
                job.job_id, result_audit_id=result_audit_id
            )

        run_candidate_jobs(
            jobs,
            worker,
            max_concurrency=request.max_concurrency,
        )
        refreshed_jobs = tuple(
            job_repository.get(job.job_id) or job for job in jobs
        )
        completed_results = {
            job.candidate_id: job.result_audit_id
            for job in refreshed_jobs
            if job.result_audit_id is not None
        }
        result_audit_id = None
        if len(completed_results) == len(refreshed_jobs):
            result_audit_id = RasAuditDerivationService(
                audit_repository
            ).merge_candidate_derivations(
                base_audit_id=audit_id,
                candidate_results=completed_results,
                created_at=datetime.now(UTC),
            )
            PersistedRasAuditReportService(audit_repository).generate(
                result_audit_id
            )
    except (AgentFileExpiredError, AgentFileMissingError):
        return _to_error_response(_file_missing_error())
    except ValueError:
        return _to_error_response(_file_reference_error())
    return RasCandidateJobBatchResponse(
        jobs=[
            _ras_candidate_job_response(job) for job in refreshed_jobs
        ],
        result_audit_id=result_audit_id,
    )


@router.delete(
    "/ras-audits/{audit_id}/candidate-jobs/{job_id}",
    response_model=RasCandidateJobResponse,
    responses={
        400: {"model": AgentErrorResponse},
        404: {"model": AgentErrorResponse},
        503: {"model": AgentErrorResponse},
    },
)
async def cancel_ras_candidate_job(
    audit_id: str,
    job_id: str,
    job_repository: RasCandidateJobRepositoryDependency,
) -> RasCandidateJobResponse | JSONResponse:
    if job_repository is None:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_job_repository_unavailable",
                public_message="La reprise des candidats RAS est indisponible.",
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    job = job_repository.get(job_id)
    if job is None or job.audit_id != audit_id:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_candidate_job_not_found",
                public_message="Le job candidat RAS est introuvable.",
            ),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        return _ras_candidate_job_response(job_repository.cancel(job_id))
    except ValueError:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_candidate_job_not_cancellable",
                public_message="Le job candidat RAS ne peut pas etre annule.",
            )
        )


@router.post(
    "/ras-audits/{audit_id}/candidates/{candidate_id}/assess",
    response_model=AgentRunResponse,
    responses={400: {"model": AgentErrorResponse}},
)
async def assess_ras_audit_candidate(
    audit_id: str,
    candidate_id: str,
    request: RasCandidateAssessmentRequest,
    orchestrator: AgentOrchestratorDependency,
    file_resolver: AgentFileResolverDependency,
) -> AgentRunResponse | JSONResponse:
    try:
        file_path = file_resolver.resolve_file_path(
            session_id=request.session_id,
            file_id=request.file_id,
            direct_file_path=None,
        )
        if file_path is None:
            return _to_error_response(_file_missing_error())
        result = orchestrator.run(
            AgentRunRequest(
                user_message=request.message,
                file_path=file_path,
                sheet_name=request.sheet_name,
                allowed_tools=(
                    "assess_ras_accounting",
                    "generate_ras_audit_report",
                ),
                direct_tool_call=ToolCall(
                    name="assess_ras_accounting",
                    arguments={
                        "base_audit_id": audit_id,
                        "candidate_id": candidate_id,
                    },
                ),
                session_id=request.session_id,
                file_id=request.file_id,
            )
        )
    except AgentFileExpiredError:
        return _to_error_response(_file_expired_error())
    except AgentFileMissingError:
        return _to_error_response(_file_missing_error())
    except ValueError:
        return _to_error_response(_file_reference_error())
    if any(not tool_result.ok for tool_result in result.tool_results):
        return _to_error_response(
            AgentEndpointError(
                public_code=(
                    next(
                        (
                            tool_result.error_code
                            for tool_result in result.tool_results
                            if not tool_result.ok and tool_result.error_code
                        ),
                        "ras_candidate_assessment_failed",
                    )
                ),
                public_message="Le candidat RAS n'a pas pu etre evalue.",
            )
        )
    return _to_agent_run_response(result)


@router.get(
    "/ras-audits/{audit_id}/report",
    response_model=None,
    responses={
        404: {"model": AgentErrorResponse},
        503: {"model": AgentErrorResponse},
    },
)
async def download_ras_audit_report(
    audit_id: str,
    repository: RasAuditRepositoryDependency,
    session_id: Annotated[str, Query(min_length=1)],
    file_id: Annotated[str, Query(min_length=1)],
    report_format: Annotated[
        Literal["csv", "json", "xlsx", "pdf"], Query(alias="format")
    ] = "csv",
    preview: bool = False,
) -> Response | JSONResponse:
    if repository is None:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_audit_repository_unavailable",
                public_message="La persistance des audits RAS est indisponible.",
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    snapshot = repository.get(audit_id)
    if (
        snapshot is None
        or snapshot.session_id != session_id
        or snapshot.file_id != file_id
    ):
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_audit_report_not_found",
                public_message="Le rapport d'audit RAS demande est introuvable.",
            ),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    try:
        report = PersistedRasAuditReportService(repository).generate(audit_id)
    except PersistedRasAuditReportError:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_audit_report_not_found",
                public_message="Le rapport d'audit RAS demandé est introuvable.",
            ),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _ras_audit_report_response(
        report,
        audit_id,
        report_format,
        preview=preview and report_format == "json",
    )


@router.post(
    "/sessions/{session_id}/ras-audit-report",
    response_model=None,
    responses={
        400: {"model": AgentErrorResponse},
        404: {"model": AgentErrorResponse},
        503: {"model": AgentErrorResponse},
    },
)
async def run_and_download_ras_audit_report(
    session_id: str,
    settings: SettingsDependency,
    repository: AgentRepositoryDependency,
    ras_audit_repository: RasAuditRepositoryDependency,
    report_format: Annotated[
        Literal["csv", "json", "xlsx", "pdf"], Query(alias="format")
    ] = "csv",
    preview: bool = False,
) -> Response | JSONResponse:
    if repository is None or ras_audit_repository is None:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_audit_repository_unavailable",
                public_message="La persistance des audits RAS est indisponible.",
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if settings.ras_fact_context_signing_key is None:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_fact_context_unavailable",
                public_message="L'attestation des audits RAS n'est pas configurée.",
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    active_file = repository.get_active_file(session_id)
    if active_file is None:
        return _to_error_response(
            AgentEndpointError(
                public_code="agent_no_active_file",
                public_message="Aucun fichier actif pour cette session.",
            ),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    stored_file = repository.find_file(
        session_id=active_file.session_id,
        file_id=active_file.file_id,
    )
    if stored_file is None:
        return _to_error_response(_file_missing_error())
    if stored_file.expires_at <= datetime.now(tz=UTC):
        return _to_error_response(_file_expired_error())
    if not stored_file.path.is_file():
        return _to_error_response(_file_missing_error())
    if not active_file.sheet_names:
        return _to_error_response(
            AgentEndpointError(
                public_code="agent_file_invalid",
                public_message="Le fichier Excel actif n'a aucune feuille lisible.",
            ),
        )
    executor = create_excel_tool_executor(
        settings,
        ras_audit_repository=ras_audit_repository,
    )
    attestor = RasFactContextAttestor(
        settings.ras_fact_context_signing_key.get_secret_value(),
    )
    token = attestor.issue(
        message="",
        extraction=RasFactExtraction(
            facts=(),
            conflicting_fact_names=(),
            pattern_versions=(),
        ),
        session_id=session_id,
        file_id=active_file.file_id,
    )
    batch_result = executor.execute(
        ToolCall(
            name="run_ras_audit_batch",
            arguments={
                "file_path": str(stored_file.path),
                "sheet_name": active_file.sheet_names[0],
            },
        ),
        ras_fact_context_token=token,
    )
    if not batch_result.ok:
        return _to_error_response(
            AgentEndpointError(
                public_code=batch_result.error_code or "ras_audit_batch_failed",
                public_message="L'audit RAS n'a pas pu être exécuté.",
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    audit_id = str(batch_result.output["audit_id"])
    try:
        report = PersistedRasAuditReportService(ras_audit_repository).generate(
            audit_id
        )
    except PersistedRasAuditReportError:
        return _to_error_response(
            AgentEndpointError(
                public_code="ras_audit_report_not_found",
                public_message="Le rapport d'audit RAS demandé est introuvable.",
            ),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    response = _ras_audit_report_response(
        report,
        audit_id,
        report_format,
        preview=preview and report_format == "json",
    )
    response.headers["X-File-ID"] = active_file.file_id
    return response


@router.post(
    "/runs",
    response_model=AgentRunResponse,
    responses={400: {"model": AgentErrorResponse}},
)
async def run_agent(
    request: AgentRunHttpRequest,
    orchestrator: AgentOrchestratorDependency,
    file_resolver: AgentFileResolverDependency,
    repository: AgentRepositoryDependency,
    settings: SettingsDependency,
) -> AgentRunResponse | JSONResponse:
    try:
        file_path = file_resolver.resolve_file_path(
            session_id=request.session_id,
            file_id=request.file_id,
            direct_file_path=request.file_path,
        )
        result = orchestrator.run(
            _to_agent_run_request(
                request=request,
                file_path=file_path,
                settings=settings,
            ),
        )
        _save_agent_run_if_configured(
            request=request,
            result=result,
            repository=repository,
        )
    except AgentFileExpiredError:
        return _to_error_response(_file_expired_error())
    except AgentFileMissingError:
        return _to_error_response(_file_missing_error())
    except ValueError:
        return _to_error_response(_file_reference_error())
    except AgentEndpointError as exc:
        return _to_error_response(exc)
    return _to_agent_run_response(result)


@router.post(
    "/runs/stream",
    response_model=None,
    responses={400: {"model": AgentErrorResponse}},
)
async def stream_agent_run(
    request: AgentRunHttpRequest,
    orchestrator: AgentOrchestratorDependency,
    file_resolver: AgentFileResolverDependency,
    repository: AgentRepositoryDependency,
    settings: SettingsDependency,
) -> StreamingResponse | JSONResponse:
    try:
        file_path = file_resolver.resolve_file_path(
            session_id=request.session_id,
            file_id=request.file_id,
            direct_file_path=request.file_path,
        )
        agent_request = _to_agent_run_request(
            request=request,
            file_path=file_path,
            settings=settings,
        )
    except AgentFileExpiredError:
        return _to_error_response(_file_expired_error())
    except AgentFileMissingError:
        return _to_error_response(_file_missing_error())
    except ValueError:
        return _to_error_response(_file_reference_error())

    return StreamingResponse(
        _stream_agent_run(orchestrator, agent_request, request, repository),
        media_type="application/x-ndjson",
    )


def _build_agent_file_store(
    settings: Settings,
    repository: SqlAlchemyAgentRepository | None,
    upload_validator: AgentExcelUploadValidator | None = None,
) -> TemporaryAgentFileStore | PersistentAgentFileStore:
    if repository is None:
        return _get_agent_file_store(
            storage_root_path=settings.agent_file_storage_root_path,
            ttl_seconds=settings.agent_file_ttl_seconds,
        )
    return PersistentAgentFileStore(
        storage_root=Path(settings.agent_file_storage_root_path),
        repository=repository,
        ttl=timedelta(seconds=settings.agent_file_ttl_seconds),
        upload_validator=upload_validator,
    )


def _to_agent_run_request(
    request: AgentRunHttpRequest,
    file_path: Path | None,
    settings: Settings,
) -> AgentRunRequest:
    allowed_tools = _effective_allowed_tools(request.allowed_tools, settings)
    return AgentRunRequest(
        user_message=request.message,
        file_path=file_path,
        sheet_name=request.sheet_name,
        allowed_tools=(
            allowed_tools
            if file_path is not None
            else tuple(
                tool
                for tool in allowed_tools
                if tool in {"query_tax_rag", *ATTESTED_LEGAL_AGENT_TOOLS}
            )
        ),
        session_id=request.session_id,
        file_id=request.file_id,
        direct_tool_call=(
            ToolCall(
                name=request.requested_tool,
                arguments={
                    "file_path": str(file_path),
                    "sheet_name": request.sheet_name,
                },
            )
            if request.requested_tool and request.sheet_name and file_path
            else None
        ),
    )


def _effective_allowed_tools(
    requested_tools: list[str],
    settings: Settings,
) -> tuple[str, ...]:
    configured_defaults = list(DEFAULT_AGENT_TOOLS)
    fact_attestation_enabled = settings.ras_fact_context_signing_key is not None
    account_mapping_enabled = settings.ras_ledger_account_mapping_path is not None
    if fact_attestation_enabled:
        configured_defaults.extend(ATTESTED_LEGAL_AGENT_TOOLS)
        configured_defaults.extend(ATTESTED_PERSISTED_RAS_AGENT_TOOLS)
    if account_mapping_enabled:
        configured_defaults.extend(MAPPED_RAS_AUDIT_AGENT_TOOLS)
    if fact_attestation_enabled and account_mapping_enabled:
        configured_defaults.extend(FULLY_ATTESTED_RAS_AGENT_TOOLS)
    requested = tuple(
        tool
        for tool in requested_tools
        if _ras_tool_is_configured(
            tool,
            fact_attestation_enabled=fact_attestation_enabled,
            account_mapping_enabled=account_mapping_enabled,
        )
    )
    return tuple(dict.fromkeys((*requested, *configured_defaults)))


def _ras_tool_is_configured(
    tool: str,
    *,
    fact_attestation_enabled: bool,
    account_mapping_enabled: bool,
) -> bool:
    if tool in ATTESTED_LEGAL_AGENT_TOOLS:
        return fact_attestation_enabled
    if tool in ATTESTED_PERSISTED_RAS_AGENT_TOOLS:
        return fact_attestation_enabled
    if tool in MAPPED_RAS_AUDIT_AGENT_TOOLS:
        return account_mapping_enabled
    if tool in FULLY_ATTESTED_RAS_AGENT_TOOLS:
        return fact_attestation_enabled and account_mapping_enabled
    return True


def _save_agent_run_if_configured(
    request: AgentRunHttpRequest,
    result: AgentRunResult,
    repository: SqlAlchemyAgentRepository | None,
) -> None:
    if repository is None:
        return
    repository.save_run(
        user_message=request.message,
        result=result,
        session_id=request.session_id,
        file_id=request.file_id,
    )


def _file_reference_error() -> AgentEndpointError:
    return AgentEndpointError(
        public_code="agent_file_reference_error",
        public_message="La reference fichier agent est invalide.",
    )


def _file_missing_error() -> AgentEndpointError:
    return AgentEndpointError(
        public_code="file_missing",
        public_message="Le fichier agent est introuvable ou a ete supprime.",
    )


def _file_expired_error() -> AgentEndpointError:
    return AgentEndpointError(
        public_code="file_expired",
        public_message="Le fichier agent a expire. Veuillez le televerser a nouveau.",
    )


def _to_agent_run_response(result: AgentRunResult) -> AgentRunResponse:
    return AgentRunResponse(
        answer=result.answer,
        provider_name=result.provider_name,
        model_name=result.model_name,
        execution_events=[
            _to_agent_run_event_response(event) for event in result.execution_events
        ],
        tool_results=[
            AgentToolResultResponse(
                tool_name=tool_result.tool_name,
                ok=tool_result.ok,
                output=tool_result.output,
                error_code=tool_result.error_code,
                error_message=tool_result.error_message,
            )
            for tool_result in result.tool_results
        ],
    )


def _empty_session_context(session_id: str) -> AgentSessionContextResponse:
    return AgentSessionContextResponse(
        state="empty",
        session_id=session_id,
        active_file=None,
        files=[],
        dashboard=None,
        last_agent_events=[],
    )


def _to_agent_file_summary_response(file: AgentFileSummary) -> AgentFileSummaryResponse:
    return AgentFileSummaryResponse(
        session_id=file.session_id,
        file_id=file.file_id,
        original_filename=file.original_filename,
        file_size_bytes=file.file_size_bytes,
        sheet_names=list(file.sheet_names),
        created_at=file.created_at,
        expires_at=file.expires_at,
        status=file.status,
    )


def _to_session_context_event_response(
    event: AgentRunEventSummary,
) -> AgentSessionContextEventResponse:
    return AgentSessionContextEventResponse(
        event_type=event.event_type,
        title=event.title,
        message=event.message,
        status=event.status,
        tool_name=event.tool_name,
        provider_name=event.provider_name,
        model_name=event.model_name,
        created_at=event.created_at,
    )


def _to_agent_run_event_response(event: AgentRunEvent) -> AgentRunEventResponse:
    return AgentRunEventResponse(
        event_type=event.event_type,
        title=event.title,
        message=event.message,
        status=event.status,
        tool_name=event.tool_name,
        provider_name=event.provider_name,
        model_name=event.model_name,
    )


def _stream_agent_run(
    orchestrator: AgentOrchestrator,
    request: AgentRunRequest,
    http_request: AgentRunHttpRequest,
    repository: SqlAlchemyAgentRepository | None,
) -> Iterator[str]:
    queue: Queue[object] = Queue()

    def run_worker() -> None:
        try:
            result = orchestrator.run(request, event_sink=queue.put)
            _save_agent_run_if_configured(
                request=http_request,
                result=result,
                repository=repository,
            )
            for answer_chunk in _split_answer_for_streaming(result.answer):
                queue.put(
                    AgentRunEvent(
                        event_type="answer_delta",
                        title="Réponse en cours",
                        message=answer_chunk,
                        status="streaming",
                        provider_name=result.provider_name,
                        model_name=result.model_name,
                    ),
                )
            queue.put(result)
        except Exception:
            queue.put(
                AgentRunEvent(
                    event_type="run_failed",
                    title="Analyse interrompue",
                    message="L'analyse n'a pas pu être terminée.",
                    status="error",
                ),
            )
        finally:
            queue.put(None)

    Thread(target=run_worker, daemon=True).start()

    while True:
        item = queue.get()
        if item is None:
            break
        if isinstance(item, AgentRunEvent):
            yield _to_ndjson_line(
                event_type="event",
                data=_to_agent_run_event_response(item).model_dump(),
            )
        if isinstance(item, AgentRunResult):
            yield _to_ndjson_line(
                event_type="result",
                data=_to_agent_run_response(item).model_dump(mode="json"),
            )


def _split_answer_for_streaming(answer: str) -> Iterator[str]:
    for chunk in (part.strip() for part in answer.splitlines()):
        if chunk:
            yield chunk


def _to_ndjson_line(event_type: str, data: dict[str, object]) -> str:
    return (
        json.dumps(
            {"type": event_type, "data": data},
            ensure_ascii=False,
        )
        + "\n"
    )


def _to_error_response(
    error: AgentEndpointError,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    response = AgentErrorResponse(
        error=AgentErrorDetail(
            code=error.public_code,
            message=error.public_message,
        ),
    )
    return JSONResponse(status_code=status_code, content=response.model_dump())
