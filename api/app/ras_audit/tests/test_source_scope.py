from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from app.ledger_analysis.posting_key_rules import PostingKeyRule, load_posting_key_rules
from app.ras_audit.account_mapping import (
    RasLedgerAccountMapping,
    load_ras_ledger_account_mappings,
)
from app.ras_audit.accounting_entry import AccountingEntryReconstructor
from app.ras_audit.domain import CanonicalLedgerEntry, LedgerField
from app.ras_audit.golden_dataset import load_golden_dataset
from app.ras_audit.normalization import (
    LedgerNormalizationIssue,
    LedgerNormalizationReport,
)
from app.ras_audit.readiness import LedgerReadinessInput, assess_ledger_readiness
from app.ras_audit.source_scope import assess_uploaded_sheet_scope

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).parent / "fixtures"


def test_complete_uploaded_sheet_scope_is_server_derivable() -> None:
    entries, rules, mappings = _references()
    normalization = LedgerNormalizationReport(
        source_file_name="golden.xlsx",
        sheet_name="GL",
        bindings=(),
        entries=entries,
        rejected_rows=(),
        issues=(),
        content_sha256="a" * 64,
        readiness=assess_ledger_readiness(
            LedgerReadinessInput(available_fields=frozenset(LedgerField))
        ),
    )
    reconstruction = AccountingEntryReconstructor(rules).reconstruct(entries)

    scope = assess_uploaded_sheet_scope(
        normalization=normalization,
        reconstruction=reconstruction,
        posting_key_rules=rules,
        account_mappings=mappings,
    )

    assert scope.is_complete is True
    assert scope.blocker_codes == ()


def test_unknown_posting_key_blocks_firm_absence_finding() -> None:
    entries, rules, mappings = _references()
    entries = (replace(entries[0], posting_key="99"), *entries[1:])
    normalization = LedgerNormalizationReport(
        source_file_name="golden.xlsx",
        sheet_name="GL",
        bindings=(),
        entries=entries,
        rejected_rows=(),
        issues=(),
        content_sha256="a" * 64,
        readiness=assess_ledger_readiness(
            LedgerReadinessInput(available_fields=frozenset(LedgerField))
        ),
    )

    scope = assess_uploaded_sheet_scope(
        normalization=normalization,
        reconstruction=AccountingEntryReconstructor(rules).reconstruct(entries),
        posting_key_rules=rules,
        account_mappings=mappings,
    )

    assert scope.is_complete is False
    assert "missing_or_unknown_posting_keys" in scope.blocker_codes


def test_accounting_proxies_block_firm_absence_finding() -> None:
    entries, rules, mappings = _references()
    source = entries[0]
    normalization = replace(
        _normalization(entries),
        issues=(
            LedgerNormalizationIssue(
                line_id=source.line_id,
                row_number=source.source.row_number,
                field=LedgerField.POSTING_DATE,
                code="document_date_used_as_posting_date",
                message="proxy",
            ),
            LedgerNormalizationIssue(
                line_id=source.line_id,
                row_number=source.source.row_number,
                field=LedgerField.JOURNAL,
                code="document_type_used_as_journal",
                message="proxy",
            ),
        ),
    )

    scope = assess_uploaded_sheet_scope(
        normalization=normalization,
        reconstruction=AccountingEntryReconstructor(rules).reconstruct(entries),
        posting_key_rules=rules,
        account_mappings=mappings,
    )

    assert scope.is_complete is False
    assert {
        "posting_date_is_document_date_proxy",
        "journal_is_document_type_proxy",
    }.issubset(scope.blocker_codes)


def test_missing_technical_values_block_firm_absence_finding() -> None:
    entries, rules, mappings = _references()
    entries = (
        replace(entries[0], line_number=None),
        replace(entries[1], amount=None),
        replace(entries[2], currency=None),
        replace(entries[3], posting_date=None),
        replace(entries[4], period=None),
        *entries[5:],
    )

    scope = assess_uploaded_sheet_scope(
        normalization=_normalization(entries),
        reconstruction=AccountingEntryReconstructor(rules).reconstruct(entries),
        posting_key_rules=rules,
        account_mappings=mappings,
    )

    assert scope.is_complete is False
    assert {
        "missing_accounting_line_numbers",
        "missing_or_invalid_amounts",
        "missing_or_invalid_currencies",
        "missing_or_invalid_posting_dates",
        "missing_or_invalid_fiscal_periods",
    }.issubset(scope.blocker_codes)


def test_duplicate_and_conflicting_document_facts_block_complete_scope() -> None:
    entries, rules, mappings = _references()
    source = entries[0]
    assert source.posting_date is not None
    entries = (
        *entries,
        replace(source, line_id="duplicate-line"),
        replace(
            source,
            line_id="currency-conflict",
            line_number="998",
            currency="USD",
        ),
        replace(
            source,
            line_id="date-conflict",
            line_number="999",
            posting_date=source.posting_date + timedelta(days=1),
        ),
    )

    scope = assess_uploaded_sheet_scope(
        normalization=_normalization(entries),
        reconstruction=AccountingEntryReconstructor(rules).reconstruct(entries),
        posting_key_rules=rules,
        account_mappings=mappings,
    )

    assert scope.is_complete is False
    assert {
        "duplicate_accounting_line_numbers",
        "conflicting_document_currencies",
        "conflicting_document_posting_dates",
    }.issubset(scope.blocker_codes)


def _references() -> tuple[
    tuple[CanonicalLedgerEntry, ...],
    tuple[PostingKeyRule, ...],
    tuple[RasLedgerAccountMapping, ...],
]:
    dataset = load_golden_dataset(FIXTURES / "golden")
    all_entries = tuple(
        entry for scenario in dataset.scenarios for entry in scenario.entries
    )
    rules = load_posting_key_rules(ROOT / "docs/reference/sap-posting-key-rules.csv")
    known_keys = {rule.posting_key for rule in rules}
    entries = tuple(
        entry for entry in all_entries if entry.posting_key in known_keys
    )
    mappings = load_ras_ledger_account_mappings(
        FIXTURES / "account-mapping/valid.csv"
    )
    return entries, rules, mappings


def _normalization(
    entries: tuple[CanonicalLedgerEntry, ...],
) -> LedgerNormalizationReport:
    return LedgerNormalizationReport(
        source_file_name="golden.xlsx",
        sheet_name="GL",
        bindings=(),
        entries=entries,
        rejected_rows=(),
        issues=(),
        content_sha256="a" * 64,
        readiness=assess_ledger_readiness(
            LedgerReadinessInput(available_fields=frozenset(LedgerField))
        ),
    )
