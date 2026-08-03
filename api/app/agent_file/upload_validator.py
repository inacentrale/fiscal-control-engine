from pathlib import Path
from zipfile import BadZipFile

import pandas as pd

from app.agent_file.domain import (
    AgentFileReadError,
    AgentFileTooLargeError,
    AgentFileValidationReport,
    UnsupportedAgentFileError,
)
from app.excel_agent.constants import SUPPORTED_EXCEL_SUFFIXES


class AgentExcelUploadValidator:
    def __init__(self, max_file_size_bytes: int) -> None:
        if max_file_size_bytes < 1:
            raise ValueError("max_file_size_bytes must be positive")
        self._max_file_size_bytes = max_file_size_bytes

    def validate(self, source_path: Path) -> AgentFileValidationReport:
        resolved_source_path = source_path.resolve()
        if resolved_source_path.suffix.lower() not in SUPPORTED_EXCEL_SUFFIXES:
            raise UnsupportedAgentFileError(
                f"unsupported agent file: {resolved_source_path.suffix}",
            )
        if not resolved_source_path.is_file():
            raise AgentFileReadError("agent file does not exist")

        file_size_bytes = resolved_source_path.stat().st_size
        if file_size_bytes > self._max_file_size_bytes:
            raise AgentFileTooLargeError("agent file is too large")

        sheet_names = _read_sheet_names(resolved_source_path)
        if not sheet_names:
            raise AgentFileReadError("agent Excel file has no sheet")
        return AgentFileValidationReport(
            file_size_bytes=file_size_bytes,
            sheet_names=sheet_names,
            is_valid=True,
        )


def _read_sheet_names(source_path: Path) -> tuple[str, ...]:
    try:
        with pd.ExcelFile(source_path, engine="openpyxl") as excel_file:
            return tuple(excel_file.sheet_names)
    except (BadZipFile, OSError, ValueError) as exc:
        raise AgentFileReadError("invalid agent Excel file") from exc
