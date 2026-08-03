from pathlib import Path
from typing import Protocol

from app.agent_file.domain import (
    AgentFileUploadResult,
    AgentFileValidationReport,
    StoredAgentFile,
)
from app.agent_file.temporary_file_store import TemporaryAgentFileStore
from app.agent_file.upload_validator import AgentExcelUploadValidator


class AgentFileStore(Protocol):
    def store(
        self,
        source_path: Path,
        original_filename: str,
        session_id: str | None = None,
    ) -> StoredAgentFile:
        pass


class AgentFileUploadService:
    def __init__(
        self,
        store: AgentFileStore | TemporaryAgentFileStore,
        validator: AgentExcelUploadValidator | None = None,
    ) -> None:
        self._store = store
        self._validator = validator

    def register_upload(
        self,
        source_path: Path,
        original_filename: str,
        session_id: str | None = None,
    ) -> AgentFileUploadResult:
        validation_report = (
            self._validator.validate(source_path)
            if self._validator is not None
            else None
        )
        stored_file = self._store.store(
            source_path=source_path,
            original_filename=_sanitize_original_filename(
                original_filename,
                source_path.suffix,
            ),
            session_id=session_id,
        )
        sheet_names = (
            validation_report.sheet_names
            if validation_report is not None
            else _validate_with_default_limit(source_path).sheet_names
        )
        return AgentFileUploadResult(
            session_id=stored_file.session_id,
            file_id=stored_file.file_id,
            original_filename=stored_file.original_filename,
            expires_at=stored_file.expires_at,
            validated_for_agent=stored_file.validated_for_agent,
            rag_indexable=stored_file.rag_indexable,
            sheet_names=sheet_names,
        )


def _sanitize_original_filename(original_filename: str, suffix: str) -> str:
    filename = Path(original_filename).name.strip()
    if filename:
        return filename
    normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return f"uploaded-file{normalized_suffix}"


def _validate_with_default_limit(source_path: Path) -> AgentFileValidationReport:
    return AgentExcelUploadValidator(max_file_size_bytes=20_000_000).validate(
        source_path,
    )
