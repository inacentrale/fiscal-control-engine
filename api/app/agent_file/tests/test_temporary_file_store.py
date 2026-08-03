from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.agent_file.domain import AgentFileTooLargeError, UnsupportedAgentFileError
from app.agent_file.temporary_file_store import TemporaryAgentFileStore
from app.agent_file.upload_validator import AgentExcelUploadValidator
from app.excel_agent.tests.fixtures import write_minified_grand_livre


def test_store_creates_session_file_for_minified_grand_livre(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    store = TemporaryAgentFileStore(
        storage_root=tmp_path / "sessions",
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )

    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")

    assert stored_file.session_id
    assert stored_file.file_id
    assert stored_file.original_filename == "grand_livre.xlsx"
    assert stored_file.path.is_file()
    assert stored_file.path.is_relative_to((tmp_path / "sessions").resolve())
    assert stored_file.expires_at == datetime(2026, 1, 2, tzinfo=UTC)
    assert stored_file.validated_for_agent is True
    assert stored_file.anonymized_for_rag is False
    assert stored_file.rag_indexable is False


def test_store_rejects_non_excel_file(tmp_path: Path) -> None:
    source_path = tmp_path / "notes.txt"
    source_path.write_text("hello", encoding="utf-8")
    store = TemporaryAgentFileStore(storage_root=tmp_path / "sessions")

    with pytest.raises(UnsupportedAgentFileError):
        store.store(source_path, original_filename="notes.txt")


def test_store_validates_file_before_copying(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    store = TemporaryAgentFileStore(
        storage_root=tmp_path / "sessions",
        upload_validator=AgentExcelUploadValidator(max_file_size_bytes=1),
    )

    with pytest.raises(AgentFileTooLargeError):
        store.store(source_path, original_filename="grand_livre.xlsx")

    assert not (tmp_path / "sessions").exists()


def test_store_resolves_active_file_by_session_and_file_id(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    store = TemporaryAgentFileStore(
        storage_root=tmp_path / "sessions",
        now=lambda: now,
    )
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")

    resolved_file = store.resolve(
        session_id=stored_file.session_id,
        file_id=stored_file.file_id,
    )

    assert resolved_file == stored_file


def test_store_does_not_resolve_expired_file(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    current_time = datetime(2026, 1, 1, tzinfo=UTC)
    store = TemporaryAgentFileStore(
        storage_root=tmp_path / "sessions",
        ttl=timedelta(hours=1),
        now=lambda: current_time,
    )
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    current_time = datetime(2026, 1, 1, 2, tzinfo=UTC)

    assert (
        store.resolve(session_id=stored_file.session_id, file_id=stored_file.file_id)
        is None
    )


def test_store_returns_none_for_unknown_file(tmp_path: Path) -> None:
    store = TemporaryAgentFileStore(storage_root=tmp_path / "sessions")

    assert store.resolve(session_id="missing", file_id="missing") is None
