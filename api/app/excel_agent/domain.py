from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any


class ExcelAgentError(ValueError):
    pass


class UnsafeExcelPathError(ExcelAgentError):
    pass


class UnsupportedExcelFileError(ExcelAgentError):
    pass


class ExcelSheetNotFoundError(ExcelAgentError):
    pass


class ExcelFileReadError(ExcelAgentError):
    pass


@dataclass(frozen=True)
class ExcelSheetList:
    file_path: Path
    sheet_names: tuple[str, ...]


@dataclass(frozen=True)
class ExcelColumnList:
    file_path: Path
    sheet_name: str
    columns: tuple[str, ...]


@dataclass(frozen=True)
class ExcelColumnProfile:
    name: str
    position: int
    detected_type: str
    non_empty_count: int
    missing_count: int
    missing_ratio: float


@dataclass(frozen=True)
class ExcelSheetProfile:
    file_path: Path
    sheet_name: str
    row_count: int
    column_count: int
    columns: tuple[ExcelColumnProfile, ...]


@dataclass(frozen=True)
class ValidatedToolCall:
    name: str
    arguments: MappingProxyType[str, Any]


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_name: str
    ok: bool
    output: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None
