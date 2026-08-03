from dataclasses import replace
from pathlib import Path

from app.agent_file.rag_indexing_policy import AgentUploadRagIndexingPolicy
from app.agent_file.temporary_file_store import TemporaryAgentFileStore
from app.excel_agent.tests.fixtures import write_minified_grand_livre


def test_policy_blocks_fresh_uploaded_file_from_rag_indexing(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    store = TemporaryAgentFileStore(storage_root=tmp_path / "sessions")
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    policy = AgentUploadRagIndexingPolicy()

    assert policy.can_index(stored_file) is False
    assert policy.rejection_reason(stored_file) == "upload_not_anonymized_for_rag"


def test_policy_allows_only_validated_anonymized_indexable_file(
    tmp_path: Path,
) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    store = TemporaryAgentFileStore(storage_root=tmp_path / "sessions")
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    rag_ready_file = replace(
        stored_file,
        anonymized_for_rag=True,
        rag_indexable=True,
    )
    policy = AgentUploadRagIndexingPolicy()

    assert policy.can_index(rag_ready_file) is True
    assert policy.rejection_reason(rag_ready_file) is None
