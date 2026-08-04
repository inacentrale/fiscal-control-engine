from dataclasses import replace
from decimal import Decimal

from app.ras_audit.accounting_entry import AccountingEntryReconstructor
from app.ras_audit.counterpart import RasCounterpartFinder, RasCounterpartStatus
from app.ras_audit.tests.test_accounting_entry import (
    _normalized_entries,
    _posting_key_rules,
)
from app.ras_audit.tests.test_normalization import _account_mappings


def test_finds_same_piece_related_missing_and_currency_mismatch_cases() -> None:
    entries = _normalized_entries()
    reconstruction = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        entries
    )

    report = RasCounterpartFinder(
        posting_key_rules=_posting_key_rules(),
        account_mappings=_account_mappings(),
    ).find(
        ledger_entries=entries,
        reconstruction=reconstruction,
        source_scope_complete=True,
    )

    assert len(report.assessments) == 6
    status_counts = {
        status: sum(item.status is status for item in report.assessments)
        for status in RasCounterpartStatus
    }
    assert status_counts[RasCounterpartStatus.FOUND_IN_SAME_ENTRY] == 3
    assert status_counts[RasCounterpartStatus.POTENTIAL_RELATED_ENTRY] == 1
    assert status_counts[RasCounterpartStatus.NOT_FOUND_IN_SCOPE] == 1
    assert status_counts[RasCounterpartStatus.INDETERMINATE] == 1


def test_multiline_expense_is_assessed_once_without_double_counting_ras() -> None:
    entries = _normalized_entries()
    reconstruction = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        entries
    )

    report = RasCounterpartFinder(
        posting_key_rules=_posting_key_rules(),
        account_mappings=_account_mappings(),
    ).find(
        ledger_entries=entries,
        reconstruction=reconstruction,
        source_scope_complete=True,
    )

    multiline = next(
        item for item in report.assessments if len(item.expense_line_ids) == 2
    )
    assert multiline.status is RasCounterpartStatus.FOUND_IN_SAME_ENTRY
    assert len(multiline.counterpart_line_ids) == 1
    assert multiline.recorded_amounts[0].amount == 5000


def test_multiple_ras_lines_in_same_piece_are_summed_once() -> None:
    original = _normalized_entries()
    ras_line = next(
        line
        for line in original
        if line.account_number in {"447100", "0447100"}
        and line.amount == 5000
    )
    entries = tuple(
        replace(line, amount=Decimal("2000"))
        if line.line_id == ras_line.line_id
        else line
        for line in original
    ) + (
        replace(
            ras_line,
            line_id=f"{ras_line.line_id}-split",
            line_number=f"{ras_line.line_number}-split",
            amount=Decimal("3000"),
        ),
    )
    reconstruction = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        entries
    )

    report = RasCounterpartFinder(
        posting_key_rules=_posting_key_rules(),
        account_mappings=_account_mappings(),
    ).find(
        ledger_entries=entries,
        reconstruction=reconstruction,
        source_scope_complete=True,
    )

    split = next(
        item
        for item in report.assessments
        if len(item.counterpart_line_ids) == 2
    )
    assert split.recorded_amounts[0].amount == 5000


def test_incomplete_gl_never_emits_not_found_in_scope() -> None:
    entries = _normalized_entries()
    reconstruction = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        entries
    )

    report = RasCounterpartFinder(
        posting_key_rules=_posting_key_rules(),
        account_mappings=_account_mappings(),
    ).find(
        ledger_entries=entries,
        reconstruction=reconstruction,
        source_scope_complete=False,
    )

    assert all(
        item.status is not RasCounterpartStatus.NOT_FOUND_IN_SCOPE
        for item in report.assessments
    )


def test_same_piece_ras_keeps_later_reversal_as_potential_adjustment() -> None:
    entries = _normalized_entries()
    reconstruction = AccountingEntryReconstructor(_posting_key_rules()).reconstruct(
        entries
    )

    report = RasCounterpartFinder(
        posting_key_rules=_posting_key_rules(),
        account_mappings=_account_mappings(),
    ).find(
        ledger_entries=entries,
        reconstruction=reconstruction,
        source_scope_complete=True,
    )

    reversed_assessment = next(
        item
        for item in report.assessments
        if item.potential_adjustment_amounts
        and item.potential_adjustment_amounts[0].amount == -5000
    )
    assert reversed_assessment.status is RasCounterpartStatus.FOUND_IN_SAME_ENTRY
    assert reversed_assessment.recorded_amounts[0].amount == 5000
    assert "potential_related_adjustment_detected" in reversed_assessment.issues
