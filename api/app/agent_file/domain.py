from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class AgentFileError(ValueError):
    pass


class UnsupportedAgentFileError(AgentFileError):
    pass


class AgentFileReadError(AgentFileError):
    pass


class AgentFileTooLargeError(AgentFileError):
    pass


class AgentFileMissingError(AgentFileError):
    pass


class AgentFileExpiredError(AgentFileError):
    pass


@dataclass(frozen=True)
class AgentFileValidationReport:
    file_size_bytes: int
    sheet_names: tuple[str, ...]
    is_valid: bool


@dataclass(frozen=True)
class StoredAgentFile:
    session_id: str
    file_id: str
    original_filename: str
    path: Path
    expires_at: datetime
    validated_for_agent: bool
    anonymized_for_rag: bool
    rag_indexable: bool


@dataclass(frozen=True)
class AgentFileUploadResult:
    session_id: str
    file_id: str
    original_filename: str
    expires_at: datetime
    validated_for_agent: bool
    rag_indexable: bool
    sheet_names: tuple[str, ...]
