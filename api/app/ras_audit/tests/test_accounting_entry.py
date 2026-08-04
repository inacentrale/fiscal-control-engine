import csv
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.ledger_analysis.posting_key_rules import (
    PostingKeyRule,
    load_posting_key_rules,
)
from app.ras_audit.account_mapping import load_ras_ledger_account_mappings
from app.ras_audit.accounting_entry import AccountingEntryReconstructor
from app.ras_audit.domain import CanonicalLedgerEntry, LedgerField
from app.ras_audit.normalization import (
    LedgerColumnBinding,
    LedgerNormalizationRequest,
    LedgerNormalizer,
)


def test_reconstructs_golden_entries_without_grouping_on_amount_or_partner() -> None:
    normalized = _normalized_entries()

    report = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        normalized,
    )

    assert len(report.entries) == 11
    entry = next(
        item for item in report.entries if item.key.document_number == "SYN-PIECE-001"
    )
    assert len(entry.line_ids) == 3
    assert entry.balances[0].currency == "XOF"
    assert entry.balances[0].debit_total == Decimal("100000")
    assert entry.balances[0].credit_total == Decimal("100000")
    assert entry.balances[0].difference == 0
    assert entry.is_balanced is True


def test_unknown_posting_key_is_excluded_and_entry_is_not_balanced() -> None:
    report = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        _normalized_entries(),
    )

    entry = next(
        item for item in report.entries if item.key.document_number == "SYN-PIECE-008"
    )
    assert entry.is_balanced is False
    assert entry.balances[0].used_line_count == 1
    assert entry.balances[0].excluded_line_count == 1
    assert "unknown_posting_key" in {issue.code for issue in entry.issues}


def test_missing_explicit_key_keeps_line_ungrouped() -> None:
    source_entry = _normalized_entries()[0]
    line_without_document = replace(source_entry, document_number=None)

    report = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        (line_without_document,),
    )

    assert report.entries == ()
    assert report.ungrouped_line_ids == (source_entry.line_id,)
    assert report.issues[0].code == "missing_accounting_entry_key"


def test_same_document_number_is_separated_by_company_year_and_journal() -> None:
    source_entry = _normalized_entries()[0]
    variants = (
        source_entry,
        replace(source_entry, line_id="other-company", company_code="OTHER"),
        replace(source_entry, line_id="other-year", fiscal_year=2024),
        replace(source_entry, line_id="other-journal", journal="OD"),
    )

    report = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(variants)

    assert len(report.entries) == 4


def test_reports_duplicate_line_number_date_and_currency_conflicts() -> None:
    debit, credit = _normalized_entries()[:2]
    conflicting_credit = replace(
        credit,
        line_id="conflicting-credit",
        line_number=debit.line_number,
        posting_date=date(2025, 1, 11),
        currency="USD",
    )

    entry = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        (debit, conflicting_credit),
    ).entries[0]

    issue_codes = {issue.code for issue in entry.issues}
    assert "duplicate_accounting_line_number" in issue_codes
    assert "multiple_posting_dates" in issue_codes
    assert "multiple_document_currencies" in issue_codes
    assert entry.is_balanced is False


def test_negative_source_amount_uses_posting_key_side_and_absolute_value() -> None:
    debit, credit = _normalized_entries()[:2]
    negative_credit = replace(
        credit,
        amount=Decimal("-100000"),
    )

    entry = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        (debit, negative_credit),
    ).entries[0]

    assert entry.balances[0].debit_total == Decimal("100000")
    assert entry.balances[0].credit_total == Decimal("100000")
    assert entry.balances[0].difference == 0
    assert "negative_source_amount_normalized" in {
        issue.code for issue in entry.issues
    }
    assert entry.is_balanced is True


def _normalized_entries() -> tuple[CanonicalLedgerEntry, ...]:
    source = Path(__file__).parent / "fixtures" / "golden" / "ledger.csv"
    with source.open(encoding="utf-8", newline="") as ledger_file:
        rows = tuple(csv.DictReader(ledger_file))
    return LedgerNormalizer().normalize(
        LedgerNormalizationRequest(
            source_file_name=source.name,
            content_sha256="a" * 64,
            sheet_name="ledger",
            first_data_row=2,
            source_columns=tuple(rows[0]),
            rows=rows,
            bindings=tuple(
                LedgerColumnBinding(field, field.value)
                for field in LedgerField
                if field.value in rows[0]
            ),
            known_posting_keys=frozenset({"40", "50"}),
            source_scope_complete=True,
            ras_account_mappings=load_ras_ledger_account_mappings(
                Path(__file__).parent
                / "fixtures"
                / "account-mapping"
                / "valid.csv"
            ),
        ),
    ).entries


def _posting_key_rules() -> tuple[PostingKeyRule, ...]:
    return load_posting_key_rules(
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "sap-posting-key-rules.csv"
    )
