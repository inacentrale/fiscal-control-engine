from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.agent.orchestrator import AgentRunEvent, AgentRunResult
from app.agent_file.domain import AgentFileExpiredError
from app.agent_file.persistent_file_store import PersistentAgentFileStore
from app.agent_persistence.models import (
    AgentMessageModel,
    AgentRunEventModel,
    AgentSessionModel,
    AgentToolResultModel,
    RasAuditRunModel,
)
from app.agent_persistence.repository import SqlAlchemyAgentRepository
from app.database import Base, create_database_engine, create_session_factory
from app.excel_agent.domain import ToolExecutionResult
from app.excel_agent.tests.fixtures import write_minified_grand_livre


def test_persistent_file_store_resolves_after_store_recreation(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    session_factory = _create_session_factory(tmp_path)
    repository = SqlAlchemyAgentRepository(
        session_factory=session_factory,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    store = PersistentAgentFileStore(
        storage_root=tmp_path / "sessions",
        repository=repository,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    reloaded_store = PersistentAgentFileStore(
        storage_root=tmp_path / "sessions",
        repository=repository,
        now=lambda: datetime(2026, 1, 1, 1, tzinfo=UTC),
    )

    resolved_file = reloaded_store.resolve(
        session_id=stored_file.session_id,
        file_id=stored_file.file_id,
    )

    assert resolved_file == stored_file
    assert resolved_file.path.is_file()


def test_persistent_file_store_raises_expired_error(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    current_time = datetime(2026, 1, 1, tzinfo=UTC)
    session_factory = _create_session_factory(tmp_path)
    repository = SqlAlchemyAgentRepository(
        session_factory=session_factory,
        now=lambda: current_time,
    )
    store = PersistentAgentFileStore(
        storage_root=tmp_path / "sessions",
        repository=repository,
        ttl=timedelta(hours=1),
        now=lambda: current_time,
    )
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    current_time = datetime(2026, 1, 1, 2, tzinfo=UTC)

    with pytest.raises(AgentFileExpiredError):
        store.resolve(session_id=stored_file.session_id, file_id=stored_file.file_id)


def test_repository_persists_run_messages_events_and_tool_results(
    tmp_path: Path,
) -> None:
    session_factory = _create_session_factory(tmp_path)
    repository = SqlAlchemyAgentRepository(
        session_factory=session_factory,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )

    run_id = repository.save_run(
        user_message="Montre le compte 44585100.",
        result=AgentRunResult(
            answer="20 écritures retournées.",
            provider_name="groq",
            model_name="llama",
            execution_events=(
                AgentRunEvent(
                    event_type="tool_finished",
                    title="Analyse terminée",
                    message="20 écritures retournées.",
                    status="completed",
                    tool_name="query_ledger_entries",
                ),
            ),
            tool_results=(
                ToolExecutionResult(
                    tool_name="query_ledger_entries",
                    ok=True,
                    output={"total_matches": 203, "entries": []},
                ),
            ),
        ),
    )

    with session_factory() as session:
        messages = session.query(AgentMessageModel).filter_by(run_id=run_id).all()
        events = session.query(AgentRunEventModel).filter_by(run_id=run_id).all()
        tool_results = (
            session.query(AgentToolResultModel).filter_by(run_id=run_id).all()
        )

    assert [message.role for message in messages] == ["user", "assistant"]
    assert events[0].tool_name == "query_ledger_entries"
    assert tool_results[0].output["total_matches"] == 203


def test_repository_correlates_persisted_ras_audit_with_agent_run(
    tmp_path: Path,
) -> None:
    session_factory = _create_session_factory(tmp_path)
    now = datetime(2026, 8, 4, tzinfo=UTC)
    with session_factory() as session:
        session.add(
            RasAuditRunModel(
                audit_id="audit-1",
                parent_audit_id=None,
                agent_run_id=None,
                session_id=None,
                file_id=None,
                source_sha256="a" * 64,
                status="candidate_inventory_pending_legal_facts",
                reference_versions=["mapping-v1"],
                fact_context={"mode": "gl_only_batch"},
                created_at=now,
            )
        )
        session.commit()
    repository = SqlAlchemyAgentRepository(
        session_factory=session_factory,
        now=lambda: now,
    )

    run_id = repository.save_run(
        user_message="Audite la RAS",
        result=AgentRunResult(
            answer="Audit créé.",
            provider_name="internal",
            model_name="deterministic",
            execution_events=(),
            tool_results=(
                ToolExecutionResult(
                    tool_name="run_ras_audit_batch",
                    ok=True,
                    output={"audit_id": "audit-1", "candidate_count": 2},
                ),
            ),
        ),
    )

    with session_factory() as session:
        audit = session.get(RasAuditRunModel, "audit-1")
        assert audit is not None
        assert audit.agent_run_id == run_id


def test_repository_persists_safe_ras_fact_attestation_only(
    tmp_path: Path,
) -> None:
    session_factory = _create_session_factory(tmp_path)
    repository = SqlAlchemyAgentRepository(session_factory=session_factory)
    attestation = {
        "message_sha256": "a" * 64,
        "issued_at": "2026-08-04T12:00:00+00:00",
        "pattern_versions": ["2026.1"],
        "fact_names": ["residence_status", "tax_base_amount"],
        "evidence_references": [
            f"user_message:{'a' * 64}:chars:0-20:pattern:resident-1"
        ],
        "conflicting_fact_names": [],
    }

    run_id = repository.save_run(
        user_message="Le prestataire est resident.",
        result=AgentRunResult(
            answer="Regle provisoire identifiee.",
            provider_name="internal",
            model_name="deterministic",
            execution_events=(),
            tool_results=(
                ToolExecutionResult(
                    tool_name="resolve_applicable_ras_rule",
                    ok=True,
                    output={
                        "status": "resolved_provisional",
                        "fact_attestation": attestation,
                    },
                ),
            ),
        ),
    )

    with session_factory() as session:
        stored = session.query(AgentToolResultModel).filter_by(run_id=run_id).one()

    persisted = stored.output["fact_attestation"]
    assert persisted == attestation
    assert "token" not in repr(persisted).lower()
    assert "signing" not in repr(persisted).lower()
    assert "tax_base_amount" in persisted["fact_names"]


def test_repository_lists_recent_conversations_and_files(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    session_factory = _create_session_factory(tmp_path)
    repository = SqlAlchemyAgentRepository(
        session_factory=session_factory,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    store = PersistentAgentFileStore(
        storage_root=tmp_path / "sessions",
        repository=repository,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    repository.save_run(
        user_message="Montre les écritures du compte 44585100.",
        result=AgentRunResult(
            answer="20 écritures retournées.",
            provider_name="groq",
            model_name="llama",
            execution_events=(),
            tool_results=(),
        ),
        session_id=stored_file.session_id,
        file_id=stored_file.file_id,
    )

    conversations = repository.list_recent_conversations()
    files = repository.list_recent_files()

    assert len(conversations) == 1
    assert conversations[0].title == "Montre les écritures du compte 44585100."
    assert conversations[0].status == "Réponse agent"
    assert conversations[0].session_id == stored_file.session_id
    assert len(files) == 1
    assert files[0].original_filename == "grand_livre.xlsx"
    assert files[0].sheet_names == ("Grand Livre",)


def test_repository_tracks_active_file_inside_session(tmp_path: Path) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    session_factory = _create_session_factory(tmp_path)
    repository = SqlAlchemyAgentRepository(
        session_factory=session_factory,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    store = PersistentAgentFileStore(
        storage_root=tmp_path / "sessions",
        repository=repository,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    first_file = store.store(source_path, original_filename="first.xlsx")
    second_file = store.store(
        source_path,
        original_filename="second.xlsx",
        session_id=first_file.session_id,
    )

    active_file = repository.get_active_file(first_file.session_id)
    session_files = repository.list_session_files(first_file.session_id)

    assert second_file.session_id == first_file.session_id
    assert active_file is not None
    assert active_file.file_id == second_file.file_id
    assert [file.original_filename for file in session_files] == [
        "second.xlsx",
        "first.xlsx",
    ]
    with session_factory() as session:
        session_model = session.get(AgentSessionModel, first_file.session_id)
    assert session_model is not None
    assert session_model.active_file_id == second_file.file_id


def test_repository_groups_searches_and_restores_session_conversation(
    tmp_path: Path,
) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    current_time = datetime(2026, 1, 1, tzinfo=UTC)
    session_factory = _create_session_factory(tmp_path)
    repository = SqlAlchemyAgentRepository(
        session_factory=session_factory,
        now=lambda: current_time,
    )
    store = PersistentAgentFileStore(
        storage_root=tmp_path / "sessions",
        repository=repository,
        now=lambda: current_time,
    )
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    first_run_id = repository.save_run(
        user_message="Montre le compte fournisseur.",
        result=_simple_result("Première réponse."),
        session_id=stored_file.session_id,
        file_id=stored_file.file_id,
    )
    current_time = datetime(2026, 1, 1, 1, tzinfo=UTC)
    second_run_id = repository.save_run(
        user_message="Quel est son solde ?",
        result=_simple_result("Deuxième réponse."),
        session_id=stored_file.session_id,
        file_id=stored_file.file_id,
    )

    conversations = repository.list_recent_conversations()
    search_results = repository.list_recent_conversations(search="fournisseur")
    detail = repository.get_conversation(second_run_id)

    assert len(conversations) == 1
    assert conversations[0].run_id == second_run_id
    assert search_results[0].run_id == first_run_id
    assert detail is not None
    assert [message.content for message in detail.messages] == [
        "Montre le compte fournisseur.",
        "Première réponse.",
        "Quel est son solde ?",
        "Deuxième réponse.",
    ]


def test_repository_deletes_complete_conversation_but_keeps_file(
    tmp_path: Path,
) -> None:
    source_path = write_minified_grand_livre(tmp_path / "sources")
    session_factory = _create_session_factory(tmp_path)
    repository = SqlAlchemyAgentRepository(session_factory=session_factory)
    store = PersistentAgentFileStore(
        storage_root=tmp_path / "sessions",
        repository=repository,
    )
    stored_file = store.store(source_path, original_filename="grand_livre.xlsx")
    first_run_id = repository.save_run(
        user_message="Première question",
        result=_simple_result("Première réponse"),
        session_id=stored_file.session_id,
        file_id=stored_file.file_id,
    )
    second_run_id = repository.save_run(
        user_message="Deuxième question",
        result=_simple_result("Deuxième réponse"),
        session_id=stored_file.session_id,
        file_id=stored_file.file_id,
    )

    deleted = repository.delete_conversation(second_run_id)

    assert deleted is True
    assert repository.get_conversation(first_run_id) is None
    assert repository.get_conversation(second_run_id) is None
    assert repository.list_recent_conversations() == ()
    assert repository.find_file(stored_file.session_id, stored_file.file_id) is not None
    assert repository.delete_conversation(second_run_id) is False


def _simple_result(answer: str) -> AgentRunResult:
    return AgentRunResult(
        answer=answer,
        provider_name="groq",
        model_name="llama",
        execution_events=(),
        tool_results=(),
    )


def _create_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'agent.db'}")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)
