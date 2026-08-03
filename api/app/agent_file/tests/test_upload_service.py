from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.agent_file.domain import AgentFileTooLargeError
from app.agent_file.temporary_file_store import TemporaryAgentFileStore
from app.agent_file.upload_service import AgentFileUploadService
from app.agent_file.upload_validator import AgentExcelUploadValidator
from app.excel_agent.tests.fixtures import write_minified_grand_livre


def test_upload_service_returns_session_reference_without_server_path(
    tmp_path: Path,
) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    store = TemporaryAgentFileStore(
        storage_root=tmp_path / "sessions",
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
        upload_validator=AgentExcelUploadValidator(max_file_size_bytes=200_000),
    )
    service = AgentFileUploadService(store=store)

    result = service.register_upload(
        source_path=source_path,
        original_filename="../client/grand_livre.xlsx",
    )

    assert result.session_id
    assert result.file_id
    assert result.original_filename == "grand_livre.xlsx"
    assert result.expires_at == datetime(2026, 1, 2, tzinfo=UTC)
    assert result.validated_for_agent is True
    assert result.rag_indexable is False
    assert result.sheet_names == ("Grand Livre",)
    assert "sessions" not in repr(result)
    assert str(tmp_path) not in repr(result)


def test_upload_service_rejects_invalid_upload_before_returning_reference(
    tmp_path: Path,
) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    store = TemporaryAgentFileStore(
        storage_root=tmp_path / "sessions",
        upload_validator=AgentExcelUploadValidator(max_file_size_bytes=1),
    )
    service = AgentFileUploadService(store=store)

    with pytest.raises(AgentFileTooLargeError):
        service.register_upload(
            source_path=source_path,
            original_filename="grand_livre.xlsx",
        )


def test_upload_service_falls_back_to_safe_unknown_filename(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    store = TemporaryAgentFileStore(
        storage_root=tmp_path / "sessions",
        upload_validator=AgentExcelUploadValidator(max_file_size_bytes=200_000),
    )
    service = AgentFileUploadService(store=store)

    result = service.register_upload(source_path=source_path, original_filename="")

    assert result.original_filename == "uploaded-file.xlsx"
