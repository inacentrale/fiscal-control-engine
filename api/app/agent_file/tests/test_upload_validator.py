from pathlib import Path

import pytest

from app.agent_file.domain import (
    AgentFileReadError,
    AgentFileTooLargeError,
    UnsupportedAgentFileError,
)
from app.agent_file.upload_validator import AgentExcelUploadValidator
from app.excel_agent.tests.fixtures import write_minified_grand_livre


def test_validator_accepts_minified_grand_livre(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path)
    validator = AgentExcelUploadValidator(max_file_size_bytes=200_000)

    report = validator.validate(source_path)

    assert report.file_size_bytes > 0
    assert report.sheet_names == ("Grand Livre",)
    assert report.is_valid is True


def test_validator_rejects_missing_file(tmp_path: Path) -> None:
    validator = AgentExcelUploadValidator(max_file_size_bytes=200_000)

    with pytest.raises(AgentFileReadError):
        validator.validate(tmp_path / "missing.xlsx")


def test_validator_rejects_unsupported_extension(tmp_path: Path) -> None:
    source_path = tmp_path / "notes.txt"
    source_path.write_text("hello", encoding="utf-8")
    validator = AgentExcelUploadValidator(max_file_size_bytes=200_000)

    with pytest.raises(UnsupportedAgentFileError):
        validator.validate(source_path)


def test_validator_rejects_oversized_file(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path)
    validator = AgentExcelUploadValidator(max_file_size_bytes=1)

    with pytest.raises(AgentFileTooLargeError):
        validator.validate(source_path)


def test_validator_rejects_corrupted_excel_file(tmp_path: Path) -> None:
    source_path = tmp_path / "corrupted.xlsx"
    source_path.write_text("not a workbook", encoding="utf-8")
    validator = AgentExcelUploadValidator(max_file_size_bytes=200_000)

    with pytest.raises(AgentFileReadError):
        validator.validate(source_path)
