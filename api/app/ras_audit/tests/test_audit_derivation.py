from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, create_database_engine, create_session_factory
from app.ras_audit.audit_derivation import (
    RasAuditDerivationError,
    RasAuditDerivationService,
)
from app.ras_audit.persistence import (
    RasAuditCaseSnapshot,
    RasAuditSnapshot,
    SqlAlchemyRasAuditRepository,
)


def test_replaces_one_case_in_a_new_immutable_audit_version(tmp_path: Path) -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory(tmp_path))
    repository.save(_base_snapshot())
    replacement = _case("entry-1", "provisional_reconciled")

    derived_id = RasAuditDerivationService(repository).replace_case(
        base_audit_id="base-audit",
        source_sha256="a" * 64,
        replacement=replacement,
        added_reference_versions=("legal-v1",),
        fact_context={"message_sha256": "b" * 64},
        created_at=datetime(2026, 8, 4, 13, tzinfo=UTC),
    )

    base = repository.get("base-audit")
    derived = repository.get(derived_id)
    assert base is not None and derived is not None
    assert base.cases[0].status == "applicability_probable_to_confirm"
    assert derived.parent_audit_id == "base-audit"
    assert derived.cases[0].status == "provisional_reconciled"
    assert derived.cases[1] == base.cases[1]
    assert derived.reference_versions == ("legal-v1", "mapping-v1")
    assert repository.list_events(derived_id)[0].event_type == "audit_derived"


def test_rejects_candidate_not_present_in_base_audit(tmp_path: Path) -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory(tmp_path))
    repository.save(_base_snapshot())

    with pytest.raises(RasAuditDerivationError, match="does not belong"):
        RasAuditDerivationService(repository).replace_case(
            base_audit_id="base-audit",
            source_sha256="a" * 64,
            replacement=_case("other-entry", "provisional_reconciled"),
            added_reference_versions=("legal-v1",),
            fact_context={},
            created_at=datetime(2026, 8, 4, 13, tzinfo=UTC),
        )


def test_retry_returns_existing_immutable_derivation() -> None:
    repository = SqlAlchemyRasAuditRepository(_memory_session_factory())
    repository.save(_base_snapshot())
    service = RasAuditDerivationService(repository)
    def derive() -> str:
        return service.replace_case(
            base_audit_id="base-audit",
            source_sha256="a" * 64,
            replacement=_case("entry-1", "provisional_reconciled"),
            added_reference_versions=("legal-v1",),
            fact_context={"message_sha256": "b" * 64},
            created_at=datetime(2026, 8, 4, 13, tzinfo=UTC),
        )

    first_id = derive()
    retry_id = derive()

    assert retry_id == first_id
    assert len(repository.list_events(first_id)) == 1


def _base_snapshot() -> RasAuditSnapshot:
    return RasAuditSnapshot(
        audit_id="base-audit",
        source_sha256="a" * 64,
        status="candidate_inventory_pending_legal_facts",
        reference_versions=("mapping-v1",),
        fact_context={"mode": "gl_only_batch"},
        cases=(
            _case("entry-1", "applicability_probable_to_confirm"),
            _case("entry-2", "indeterminate_missing_data"),
        ),
        created_at=datetime(2026, 8, 4, 12, tzinfo=UTC),
    )


def _case(candidate_id: str, status: str) -> RasAuditCaseSnapshot:
    if status == "provisional_reconciled":
        certainty = "supported_provisional"
    elif status == "indeterminate_missing_data":
        certainty = "indeterminate"
    else:
        certainty = "potential"
    return RasAuditCaseSnapshot(
        candidate_id=candidate_id,
        status=status,
        certainty=certainty,
        payload={"candidate_id": candidate_id, "status": status},
    )


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'derivation.db'}")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


def _memory_session_factory() -> sessionmaker[Session]:
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)
