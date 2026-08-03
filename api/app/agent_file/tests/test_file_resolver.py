from pathlib import Path

import pytest

from app.agent_file.file_resolver import AgentFileResolver
from app.agent_file.temporary_file_store import TemporaryAgentFileStore
from app.excel_agent.tests.fixtures import write_minified_grand_livre


def test_resolver_returns_stored_file_path_from_session_reference(
    tmp_path: Path,
) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    store = TemporaryAgentFileStore(storage_root=tmp_path / "sessions")
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    resolver = AgentFileResolver(store=store)

    resolved_path = resolver.resolve_file_path(
        session_id=stored_file.session_id,
        file_id=stored_file.file_id,
        direct_file_path=None,
    )

    assert resolved_path == stored_file.path


def test_resolver_rejects_unknown_session_reference(tmp_path: Path) -> None:
    store = TemporaryAgentFileStore(storage_root=tmp_path / "sessions")
    resolver = AgentFileResolver(store=store)

    with pytest.raises(ValueError, match="unknown or expired agent file"):
        resolver.resolve_file_path(
            session_id="missing",
            file_id="missing",
            direct_file_path=None,
        )


def test_resolver_keeps_direct_file_path_for_current_non_upload_flow(
    tmp_path: Path,
) -> None:
    store = TemporaryAgentFileStore(storage_root=tmp_path / "sessions")
    resolver = AgentFileResolver(store=store)

    resolved_path = resolver.resolve_file_path(
        session_id=None,
        file_id=None,
        direct_file_path="grand_livre_minifie.xlsx",
    )

    assert resolved_path == Path("grand_livre_minifie.xlsx")


def test_resolver_rejects_ambiguous_direct_and_session_file_inputs(
    tmp_path: Path,
) -> None:
    store = TemporaryAgentFileStore(storage_root=tmp_path / "sessions")
    resolver = AgentFileResolver(store=store)

    with pytest.raises(ValueError, match="choose either"):
        resolver.resolve_file_path(
            session_id="session",
            file_id="file",
            direct_file_path="grand_livre_minifie.xlsx",
        )
