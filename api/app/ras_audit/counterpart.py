from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.ledger_analysis.posting_key_rules import PostingKeyRule
from app.ras_audit.account_mapping import (
    RasLedgerAccountMapping,
    RasLedgerAccountRole,
    best_account_mapping,
    has_applicable_ras_payable_mapping,
)
from app.ras_audit.accounting_entry import (
    AccountingEntryReconstructionReport,
    ReconstructedAccountingEntry,
)
from app.ras_audit.domain import CanonicalLedgerEntry


class RasCounterpartStatus(StrEnum):
    FOUND_IN_SAME_ENTRY = "found_in_same_entry"
    POTENTIAL_RELATED_ENTRY = "potential_related_entry"
    NOT_FOUND_IN_SCOPE = "not_found_in_scope"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class RasCounterpartAmount:
    currency: str
    amount: Decimal


@dataclass(frozen=True)
class RasCounterpartAssessment:
    candidate_entry_id: str
    expense_line_ids: tuple[str, ...]
    status: RasCounterpartStatus
    counterpart_line_ids: tuple[str, ...]
    recorded_amounts: tuple[RasCounterpartAmount, ...]
    potential_adjustment_line_ids: tuple[str, ...]
    potential_adjustment_amounts: tuple[RasCounterpartAmount, ...]
    missing_facts: tuple[str, ...]
    issues: tuple[str, ...]


@dataclass(frozen=True)
class RasCounterpartReport:
    assessments: tuple[RasCounterpartAssessment, ...]


@dataclass(frozen=True)
class RasCounterpartToolReport:
    sheet_name: str
    source_row_count: int
    rejected_row_count: int
    normalization_issue_codes: tuple[str, ...]
    source_scope_complete: bool
    source_scope_blockers: tuple[str, ...]
    source_scope_policy_version: str
    report: RasCounterpartReport
    detected_candidate_piece_count: int | None = None
    selector: dict[str, str | int | None] | None = None
    selected_entry: ReconstructedAccountingEntry | None = None
    selected_lines: tuple[CanonicalLedgerEntry, ...] = ()


class RasCounterpartFinder:
    def __init__(
        self,
        *,
        posting_key_rules: tuple[PostingKeyRule, ...],
        account_mappings: tuple[RasLedgerAccountMapping, ...],
        related_window_days: int = 31,
    ) -> None:
        if related_window_days < 0:
            raise ValueError("related window days cannot be negative")
        self._posting_key_sides = {
            rule.posting_key: rule.side for rule in posting_key_rules
        }
        self._account_mappings = account_mappings
        self._related_window_days = related_window_days

    def find(
        self,
        *,
        ledger_entries: tuple[CanonicalLedgerEntry, ...],
        reconstruction: AccountingEntryReconstructionReport,
        source_scope_complete: bool,
    ) -> RasCounterpartReport:
        lines_by_id = {entry.line_id: entry for entry in ledger_entries}
        ras_lines = tuple(
            entry
            for entry in ledger_entries
            if self._mapping(entry, RasLedgerAccountRole.RAS_PAYABLE) is not None
        )
        assessments: list[RasCounterpartAssessment] = []
        for accounting_entry in reconstruction.entries:
            lines = tuple(
                lines_by_id[line_id]
                for line_id in accounting_entry.line_ids
                if line_id in lines_by_id
            )
            expense_lines = tuple(
                line
                for line in lines
                if self._is_normal_side(
                    line,
                    self._mapping(line, RasLedgerAccountRole.EXPENSE_CANDIDATE),
                )
            )
            if not expense_lines:
                continue
            same_entry_counterparts = tuple(
                line
                for line in lines
                if self._mapping(line, RasLedgerAccountRole.RAS_PAYABLE)
                is not None
            )
            assessments.append(
                self._assess(
                    candidate_entry_id=accounting_entry.entry_id,
                    expense_lines=expense_lines,
                    same_entry_counterparts=same_entry_counterparts,
                    all_ras_lines=ras_lines,
                    source_scope_complete=source_scope_complete,
                ),
            )
        return RasCounterpartReport(assessments=tuple(assessments))

    def _assess(
        self,
        *,
        candidate_entry_id: str,
        expense_lines: tuple[CanonicalLedgerEntry, ...],
        same_entry_counterparts: tuple[CanonicalLedgerEntry, ...],
        all_ras_lines: tuple[CanonicalLedgerEntry, ...],
        source_scope_complete: bool,
    ) -> RasCounterpartAssessment:
        search_facts, missing_facts = _search_facts(expense_lines)
        if same_entry_counterparts:
            potential_adjustments = (
                self._related_lines(
                    search_facts,
                    all_ras_lines,
                    excluded_line_ids=frozenset(
                        line.line_id for line in same_entry_counterparts
                    ),
                    same_currency=True,
                )
                if search_facts is not None
                else ()
            )
            return self._assessment(
                candidate_entry_id,
                expense_lines,
                RasCounterpartStatus.FOUND_IN_SAME_ENTRY,
                same_entry_counterparts,
                potential_adjustment_lines=potential_adjustments,
                issues=(
                    ("potential_related_adjustment_detected",)
                    if potential_adjustments
                    else ()
                ),
            )

        if search_facts is None:
            return self._assessment(
                candidate_entry_id,
                expense_lines,
                RasCounterpartStatus.INDETERMINATE,
                (),
                missing_facts=missing_facts,
            )
        company_code, _, _, _, posting_date = search_facts
        related = self._related_lines(
            search_facts,
            all_ras_lines,
            excluded_line_ids=frozenset(
                item.line_id for item in expense_lines
            ),
            same_currency=True,
        )
        if related:
            return self._assessment(
                candidate_entry_id,
                expense_lines,
                RasCounterpartStatus.POTENTIAL_RELATED_ENTRY,
                related,
                issues=("document_link_not_confirmed",),
            )
        cross_currency = self._related_lines(
            search_facts,
            all_ras_lines,
            excluded_line_ids=frozenset(),
            same_currency=False,
        )
        if cross_currency:
            return self._assessment(
                candidate_entry_id,
                expense_lines,
                RasCounterpartStatus.INDETERMINATE,
                cross_currency,
                issues=("potential_counterpart_currency_mismatch",),
            )
        mapping_available = has_applicable_ras_payable_mapping(
            self._account_mappings,
            posting_date=posting_date,
            company_code=company_code,
        )
        if source_scope_complete and mapping_available:
            return self._assessment(
                candidate_entry_id,
                expense_lines,
                RasCounterpartStatus.NOT_FOUND_IN_SCOPE,
                (),
            )
        missing = []
        if not source_scope_complete:
            missing.append("source_scope_completeness")
        if not mapping_available:
            missing.append("applicable_ras_account_mapping")
        return self._assessment(
            candidate_entry_id,
            expense_lines,
            RasCounterpartStatus.INDETERMINATE,
            (),
            missing_facts=tuple(missing),
        )

    def _assessment(
        self,
        candidate_entry_id: str,
        expense_lines: tuple[CanonicalLedgerEntry, ...],
        status: RasCounterpartStatus,
        counterpart_lines: tuple[CanonicalLedgerEntry, ...],
        *,
        missing_facts: tuple[str, ...] = (),
        issues: tuple[str, ...] = (),
        potential_adjustment_lines: tuple[CanonicalLedgerEntry, ...] = (),
    ) -> RasCounterpartAssessment:
        return RasCounterpartAssessment(
            candidate_entry_id=candidate_entry_id,
            expense_line_ids=tuple(line.line_id for line in expense_lines),
            status=status,
            counterpart_line_ids=tuple(line.line_id for line in counterpart_lines),
            recorded_amounts=self._recorded_amounts(counterpart_lines),
            potential_adjustment_line_ids=tuple(
                line.line_id for line in potential_adjustment_lines
            ),
            potential_adjustment_amounts=self._recorded_amounts(
                potential_adjustment_lines
            ),
            missing_facts=missing_facts,
            issues=issues,
        )

    def _related_lines(
        self,
        search_facts: tuple[str, int, str, str, date],
        all_ras_lines: tuple[CanonicalLedgerEntry, ...],
        *,
        excluded_line_ids: frozenset[str],
        same_currency: bool,
    ) -> tuple[CanonicalLedgerEntry, ...]:
        company_code, fiscal_year, partner_id, currency, posting_date = search_facts
        return tuple(
            line
            for line in all_ras_lines
            if line.line_id not in excluded_line_ids
            and line.company_code == company_code
            and line.fiscal_year == fiscal_year
            and line.partner_id == partner_id
            and line.currency is not None
            and ((line.currency == currency) is same_currency)
            and line.posting_date is not None
            and abs((line.posting_date - posting_date).days)
            <= self._related_window_days
        )

    def _recorded_amounts(
        self,
        lines: tuple[CanonicalLedgerEntry, ...],
    ) -> tuple[RasCounterpartAmount, ...]:
        amounts: dict[str, Decimal] = {}
        for line in lines:
            mapping = self._mapping(line, RasLedgerAccountRole.RAS_PAYABLE)
            side = self._posting_key_sides.get(line.posting_key or "")
            if mapping is None or side is None or line.amount is None:
                continue
            if line.currency is None:
                continue
            normal_sign = 1 if side == mapping.normal_side.value else -1
            amounts[line.currency] = amounts.get(
                line.currency,
                Decimal("0"),
            ) + (abs(line.amount) * normal_sign)
        return tuple(
            RasCounterpartAmount(currency, amount)
            for currency, amount in sorted(amounts.items())
        )

    def _mapping(
        self,
        entry: CanonicalLedgerEntry,
        role: RasLedgerAccountRole,
    ) -> RasLedgerAccountMapping | None:
        if entry.account_number is None or entry.posting_date is None:
            return None
        return best_account_mapping(
            self._account_mappings,
            entry.account_number,
            role=role,
            posting_date=entry.posting_date,
            company_code=entry.company_code,
        )

    def _is_normal_side(
        self,
        entry: CanonicalLedgerEntry,
        mapping: RasLedgerAccountMapping | None,
    ) -> bool:
        if mapping is None or entry.posting_key is None:
            return False
        posting_side = self._posting_key_sides.get(entry.posting_key)
        return posting_side == mapping.normal_side.value


def _search_facts(
    expense_lines: tuple[CanonicalLedgerEntry, ...],
) -> tuple[tuple[str, int, str, str, date] | None, tuple[str, ...]]:
    missing: list[str] = []
    companies = {line.company_code for line in expense_lines if line.company_code}
    years = {line.fiscal_year for line in expense_lines if line.fiscal_year}
    partners = {line.partner_id for line in expense_lines if line.partner_id}
    currencies = {line.currency for line in expense_lines if line.currency}
    dates = {line.posting_date for line in expense_lines if line.posting_date}
    for name, values in (
        ("company_code", companies),
        ("fiscal_year", years),
        ("partner_id", partners),
        ("currency", currencies),
        ("posting_date", dates),
    ):
        if len(values) != 1:
            missing.append(name)
    if missing:
        return None, tuple(missing)
    return (
        (
            next(iter(companies)),
            next(iter(years)),
            next(iter(partners)),
            next(iter(currencies)),
            next(iter(dates)),
        ),
        (),
    )
