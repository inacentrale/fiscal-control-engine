from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from shutil import copyfile
from uuid import uuid4

from app.agent_file.domain import (
    AgentFileExpiredError,
    AgentFileMissingError,
    StoredAgentFile,
    UnsupportedAgentFileError,
)
from app.agent_file.upload_validator import AgentExcelUploadValidator
from app.agent_persistence.repository import SqlAlchemyAgentRepository
from app.excel_agent.constants import SUPPORTED_EXCEL_SUFFIXES


class PersistentAgentFileStore:
    def __init__(
        self,
        storage_root: Path,
        repository: SqlAlchemyAgentRepository,
        ttl: timedelta = timedelta(days=1),
        now: Callable[[], datetime] | None = None,
        upload_validator: AgentExcelUploadValidator | None = None,
    ) -> None:
        if ttl.total_seconds() <= 0:
            raise ValueError("ttl must be positive")
        self._storage_root = storage_root.resolve()
        self._repository = repository
        self._ttl = ttl
        self._now = now or (lambda: datetime.now(tz=UTC))
        self._upload_validator = upload_validator

    def store(
        self,
        source_path: Path,
        original_filename: str,
        session_id: str | None = None,
    ) -> StoredAgentFile:
        resolved_source_path = source_path.resolve()
        suffix = resolved_source_path.suffix.lower()
        if suffix not in SUPPORTED_EXCEL_SUFFIXES:
            raise UnsupportedAgentFileError(f"unsupported agent file: {suffix}")
        validation_report = (
            self._upload_validator
            or AgentExcelUploadValidator(max_file_size_bytes=20_000_000)
        ).validate(resolved_source_path)

        target_session_id = session_id or uuid4().hex
        file_id = uuid4().hex
        session_directory = self._storage_root / target_session_id
        session_directory.mkdir(parents=True, exist_ok=True)
        stored_path = session_directory / f"{file_id}{suffix}"
        copyfile(resolved_source_path, stored_path)

        stored_file = StoredAgentFile(
            session_id=target_session_id,
            file_id=file_id,
            original_filename=original_filename,
            path=stored_path.resolve(),
            expires_at=self._now() + self._ttl,
            validated_for_agent=True,
            anonymized_for_rag=False,
            rag_indexable=False,
        )
        self._repository.save_file(
            stored_file=stored_file,
            file_size_bytes=resolved_source_path.stat().st_size,
            sheet_names=validation_report.sheet_names,
        )
        return stored_file

    def resolve(self, session_id: str, file_id: str) -> StoredAgentFile:
        stored_file = self._repository.find_file(session_id=session_id, file_id=file_id)
        if stored_file is None:
            raise AgentFileMissingError("agent file reference is unknown")
        if stored_file.expires_at <= self._now():
            raise AgentFileExpiredError("agent file has expired")
        if not stored_file.path.is_relative_to(self._storage_root):
            raise AgentFileMissingError("agent file path is invalid")
        if not stored_file.path.is_file():
            raise AgentFileMissingError("agent file is missing from storage")
        return stored_file
