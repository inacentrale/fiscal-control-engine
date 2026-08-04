from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, create_database_engine, create_session_factory
from app.ledger_analysis.posting_key_rules import load_posting_key_rules
from app.ras_audit.account_mapping import load_ras_ledger_account_mappings
from app.ras_audit.accounting_entry import AccountingEntryReconstructor
from app.ras_audit.batch_audit import RasBatchAuditService, _case
from app.ras_audit.candidate_detection import (
    RasCandidateAssessment,
    RasCandidateDetectionReport,
    RasCandidateDetector,
    RasCandidateStatus,
)
from app.ras_audit.candidate_signals import load_ras_candidate_signals
from app.ras_audit.counterpart import (
    RasCounterpartAmount,
    RasCounterpartAssessment,
    RasCounterpartFinder,
    RasCounterpartReport,
    RasCounterpartStatus,
)
from app.ras_audit.golden_dataset import load_golden_dataset
from app.ras_audit.persistence import SqlAlchemyRasAuditRepository

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).parent / "fixtures"


def test_persists_all_candidates_without_inventing_legal_facts(
    tmp_path: Path,
) -> None:
    repository = SqlAlchemyRasAuditRepository(_session_factory(tmp_path))
    service = RasBatchAuditService(
        repository,
        now=lambda: datetime(2026, 8, 4, tzinfo=UTC),
    )

    result = service.persist(
        source_sha256="a" * 64,
        detection=RasCandidateDetectionReport(
            candidates=(
                _candidate("entry-1"),
                _candidate("entry-2", indeterminate=True),
            ),
            evaluated_piece_count=2,
            excluded_piece_count=0,
        ),
        counterparts=RasCounterpartReport(assessments=(_counterpart("entry-1"),)),
        reference_versions=("mapping-v1", "signals-v1"),
        source_scope_complete=True,
    )

    snapshot = repository.get(result.audit_id)
    assert snapshot is not None
    assert result.candidate_count == 2
    assert result.potential_count == 1
    assert result.indeterminate_count == 1
    assert snapshot.fact_context["user_fact_values_applied"] is False
    assert all(
        "legal_facts_per_candidate"
        in cast(list[object], case.payload["missing_facts"])
        for case in snapshot.cases
    )


def test_multi_category_candidate_is_marked_for_split() -> None:
    candidate = replace(
        _candidate("entry-multi"),
        operation_hints=("service_any", "construction_work"),
    )

    persisted = _case(candidate, None)

    assert "candidate_requires_category_split" in cast(
        list[object], persisted.payload["missing_facts"]
    )


def test_potential_related_ras_is_not_persisted_as_confirmed_amount() -> None:
    potential = replace(
        _counterpart("entry-possible"),
        status=RasCounterpartStatus.POTENTIAL_RELATED_ENTRY,
        issues=("document_link_not_confirmed",),
    )

    persisted = _case(_candidate("entry-possible"), potential)

    assert persisted.payload["recorded_amount"] is None
    assert "counterpart:potential_related_entry" in cast(
        list[object], persisted.payload["issues"]
    )


def test_golden_batch_has_full_candidate_recall_and_no_firm_tax_finding(
    tmp_path: Path,
) -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    entries = tuple(
        entry for scenario in dataset.scenarios for entry in scenario.entries
    )
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )
    mappings = load_ras_ledger_account_mappings(FIXTURES / "account-mapping/valid.csv")
    reconstruction = AccountingEntryReconstructor(posting_rules).reconstruct(entries)
    detection = RasCandidateDetector(
        posting_key_rules=posting_rules,
        account_mappings=mappings,
        signals=load_ras_candidate_signals(
            ROOT / "docs/reference/ras-candidate-signals.csv"
        ),
    ).detect(ledger_entries=entries, reconstruction=reconstruction)
    counterparts = RasCounterpartFinder(
        posting_key_rules=posting_rules,
        account_mappings=mappings,
    ).find(
        ledger_entries=entries,
        reconstruction=reconstruction,
        source_scope_complete=True,
    )
    repository = SqlAlchemyRasAuditRepository(_session_factory(tmp_path))

    result = RasBatchAuditService(repository).persist(
        source_sha256="a" * 64,
        detection=detection,
        counterparts=counterparts,
        reference_versions=("golden-v1",),
        source_scope_complete=True,
    )

    expected_candidates = sum(
        scenario.expected_candidate_signal for scenario in dataset.scenarios
    )
    snapshot = repository.get(result.audit_id)
    assert snapshot is not None
    assert result.candidate_count == expected_candidates
    assert all(
        case.status
        in {"applicability_probable_to_confirm", "indeterminate_missing_data"}
        for case in snapshot.cases
    )
    assert any(case.status == "indeterminate_missing_data" for case in snapshot.cases)


def _candidate(
    candidate_id: str,
    *,
    indeterminate: bool = False,
) -> RasCandidateAssessment:
    return RasCandidateAssessment(
        candidate_id=candidate_id,
        accounting_entry_id=candidate_id,
        status=(
            RasCandidateStatus.INDETERMINATE
            if indeterminate
            else RasCandidateStatus.ACCOUNT_AND_TEXT
        ),
        line_ids=(f"{candidate_id}-line",),
        signal_ids=("signal-1",),
        operation_hints=("service_any",),
        account_mapping_ids=("mapping-1",),
        amounts=(),
        missing_facts=("posting_key_side",) if indeterminate else (),
        exclusion_signal_ids=(),
    )


def _counterpart(candidate_id: str) -> RasCounterpartAssessment:
    return RasCounterpartAssessment(
        candidate_entry_id=candidate_id,
        expense_line_ids=(f"{candidate_id}-line",),
        status=RasCounterpartStatus.FOUND_IN_SAME_ENTRY,
        counterpart_line_ids=(f"{candidate_id}-ras",),
        recorded_amounts=(RasCounterpartAmount("XOF", Decimal("5000")),),
        potential_adjustment_line_ids=(),
        potential_adjustment_amounts=(),
        missing_facts=(),
        issues=(),
    )


def _session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'batch.db'}")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)
