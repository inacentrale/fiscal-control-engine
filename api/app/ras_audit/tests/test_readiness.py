from app.ras_audit.domain import AuditCapability, LedgerField
from app.ras_audit.readiness import (
    CapabilityReadinessStatus,
    LedgerReadinessInput,
    assess_ledger_readiness,
)


def test_detection_is_ready_with_account_and_label_signals() -> None:
    report = assess_ledger_readiness(
        LedgerReadinessInput(
            available_fields=frozenset(
                {
                    LedgerField.ACCOUNT_NUMBER,
                    LedgerField.LABEL,
                },
            ),
        ),
    )

    detection = report.for_capability(AuditCapability.CANDIDATE_DETECTION)
    assert detection.status is CapabilityReadinessStatus.READY
    assert detection.blockers == ()


def test_theoretical_calculation_is_blocked_without_date_currency_and_amount() -> None:
    report = assess_ledger_readiness(
        LedgerReadinessInput(
            available_fields=frozenset({LedgerField.ACCOUNT_NUMBER}),
        ),
    )

    calculation = report.for_capability(AuditCapability.THEORETICAL_CALCULATION)
    assert calculation.status is CapabilityReadinessStatus.BLOCKED
    assert set(calculation.blockers) == {
        "missing_amount",
        "missing_currency",
        "missing_posting_date",
    }


def test_counterpart_reconciliation_requires_scope_mapping_and_piece_fields() -> None:
    report = assess_ledger_readiness(
        LedgerReadinessInput(
            available_fields=frozenset(
                {
                    LedgerField.ACCOUNT_NUMBER,
                    LedgerField.AMOUNT,
                    LedgerField.CURRENCY,
                    LedgerField.POSTING_KEY,
                },
            ),
            source_scope_complete=None,
            ras_account_mapping_available=False,
            posting_keys_complete=False,
        ),
    )

    reconciliation = report.for_capability(
        AuditCapability.COUNTERPART_RECONCILIATION,
    )
    assert reconciliation.status is CapabilityReadinessStatus.BLOCKED
    assert set(reconciliation.blockers) == {
        "missing_company_code",
        "missing_document_number",
        "missing_fiscal_year",
        "missing_journal",
        "posting_keys_incomplete",
        "ras_account_mapping_unavailable",
        "source_scope_not_confirmed_complete",
    }


def test_unknown_posting_keys_degrade_detection_but_block_reconciliation() -> None:
    fields = frozenset(
        {
            LedgerField.ACCOUNT_NUMBER,
            LedgerField.LABEL,
            LedgerField.COMPANY_CODE,
            LedgerField.FISCAL_YEAR,
            LedgerField.JOURNAL,
            LedgerField.DOCUMENT_NUMBER,
            LedgerField.POSTING_KEY,
            LedgerField.AMOUNT,
            LedgerField.CURRENCY,
        },
    )
    report = assess_ledger_readiness(
        LedgerReadinessInput(
            available_fields=fields,
            source_scope_complete=True,
            ras_account_mapping_available=True,
            posting_keys_complete=False,
        ),
    )

    assert (
        report.for_capability(AuditCapability.CANDIDATE_DETECTION).status
        is CapabilityReadinessStatus.DEGRADED
    )
    assert (
        report.for_capability(AuditCapability.COUNTERPART_RECONCILIATION).status
        is CapabilityReadinessStatus.BLOCKED
    )
