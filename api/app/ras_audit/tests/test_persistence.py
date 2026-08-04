from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, create_database_engine, create_session_factory
from app.ras_audit.persistence import (
    RasAuditCaseSnapshot,
    RasAuditSnapshot,
    SqlAlchemyRasAuditRepository,
)


def test_saves_and_reloads_versioned_audit_cases(tmp_path: Path) -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory(tmp_path))
    snapshot = _snapshot()

    repository.save(snapshot)
    reloaded = repository.get("audit-1")

    assert reloaded == snapshot
    assert reloaded is not None
    assert reloaded.cases[0].payload["expected_amount"] == "5000"
    events = repository.list_events("audit-1")
    assert [(event.sequence, event.event_type) for event in events] == [
        (0, "audit_created")
    ]


def test_rejects_duplicate_candidate_ids(tmp_path: Path) -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory(tmp_path))
    case = _snapshot().cases[0]
    invalid = RasAuditSnapshot(**{**_snapshot().__dict__, "cases": (case, case)})

    with pytest.raises(ValueError, match="duplicate"):
        repository.save(invalid)


def _snapshot() -> RasAuditSnapshot:
    return RasAuditSnapshot(
        audit_id="audit-1",
        session_id=None,
        file_id=None,
        source_sha256="a" * 64,
        status="completed_provisional",
        reference_versions=("legal-2026", "assessment-v1"),
        fact_context={"message_sha256": "b" * 64, "pattern_versions": ["v1"]},
        cases=(
            RasAuditCaseSnapshot(
                candidate_id="entry-1",
                status="provisional_reconciled",
                certainty="supported_provisional",
                payload={"expected_amount": "5000", "currency": "XOF"},
            ),
        ),
        created_at=datetime(2026, 8, 4, tzinfo=UTC),
    )


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'ras-audit.db'}")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)
