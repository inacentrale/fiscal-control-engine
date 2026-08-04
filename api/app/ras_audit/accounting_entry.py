from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from app.ledger_analysis.posting_key_rules import PostingKeyRule
from app.ras_audit.domain import CanonicalLedgerEntry


@dataclass(frozen=True)
class AccountingEntryKey:
    company_code: str | None
    fiscal_year: int
    journal: str
    document_number: str


@dataclass(frozen=True)
class AccountingEntryBalance:
    currency: str
    debit_total: Decimal
    credit_total: Decimal
    difference: Decimal
    used_line_count: int
    excluded_line_count: int


class AccountingEntryIssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class AccountingEntryIssue:
    code: str
    severity: AccountingEntryIssueSeverity
    message: str
    line_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReconstructedAccountingEntry:
    entry_id: str
    key: AccountingEntryKey
    line_ids: tuple[str, ...]
    balances: tuple[AccountingEntryBalance, ...]
    issues: tuple[AccountingEntryIssue, ...]

    @property
    def is_balanced(self) -> bool:
        return (
            bool(self.balances)
            and not any(
                issue.severity is AccountingEntryIssueSeverity.ERROR
                for issue in self.issues
            )
            and all(
                balance.difference == 0 and balance.excluded_line_count == 0
                for balance in self.balances
            )
        )


@dataclass(frozen=True)
class AccountingEntryReconstructionReport:
    entries: tuple[ReconstructedAccountingEntry, ...]
    ungrouped_line_ids: tuple[str, ...]
    issues: tuple[AccountingEntryIssue, ...]


@dataclass(frozen=True)
class AccountingEntryReconstructionToolReport:
    sheet_name: str
    source_row_count: int
    normalized_issue_codes: tuple[str, ...]
    rejected_row_count: int
    reconstruction: AccountingEntryReconstructionReport


class AccountingEntryReconstructor:
    def __init__(self, posting_key_rules: tuple[PostingKeyRule, ...]) -> None:
        self._posting_key_sides = {
            rule.posting_key: rule.side for rule in posting_key_rules
        }

    def reconstruct(
        self,
        ledger_entries: tuple[CanonicalLedgerEntry, ...],
    ) -> AccountingEntryReconstructionReport:
        grouped: dict[AccountingEntryKey, list[CanonicalLedgerEntry]] = {}
        ungrouped: list[str] = []
        report_issues: list[AccountingEntryIssue] = []
        for entry in ledger_entries:
            key = _entry_key(entry)
            if key is None:
                ungrouped.append(entry.line_id)
                report_issues.append(
                    AccountingEntryIssue(
                        code="missing_accounting_entry_key",
                        severity=AccountingEntryIssueSeverity.ERROR,
                        message=(
                            "Fiscal year, journal and document number are required "
                            "to reconstruct an accounting entry"
                        ),
                        line_ids=(entry.line_id,),
                    ),
                )
                continue
            grouped.setdefault(key, []).append(entry)

        reconstructed = tuple(
            self._reconstruct_group(key, tuple(lines))
            for key, lines in grouped.items()
        )
        return AccountingEntryReconstructionReport(
            entries=reconstructed,
            ungrouped_line_ids=tuple(ungrouped),
            issues=tuple(report_issues),
        )

    def _reconstruct_group(
        self,
        key: AccountingEntryKey,
        lines: tuple[CanonicalLedgerEntry, ...],
    ) -> ReconstructedAccountingEntry:
        issues = _structural_issues(lines)
        amounts: dict[str, dict[str, Decimal | int]] = {}
        excluded_by_currency: dict[str, int] = {}
        for line in lines:
            currency = line.currency or "UNRESOLVED"
            side = (
                self._posting_key_sides.get(line.posting_key)
                if line.posting_key is not None
                else None
            )
            if line.amount is None or line.currency is None or side is None:
                excluded_by_currency[currency] = (
                    excluded_by_currency.get(currency, 0) + 1
                )
                if side is None and line.posting_key is not None:
                    issues.append(
                        _line_issue(
                            "unknown_posting_key",
                            "Posting key is absent from the supplied reference",
                            line,
                        )
                    )
                continue
            bucket = amounts.setdefault(
                line.currency,
                {"debit": Decimal("0"), "credit": Decimal("0"), "used": 0},
            )
            amount = abs(line.amount)
            bucket[side] = Decimal(bucket[side]) + amount
            bucket["used"] = int(bucket["used"]) + 1

        currencies = sorted(set(amounts) | set(excluded_by_currency))
        balances = tuple(
            _balance(
                currency,
                amounts.get(currency),
                excluded_by_currency.get(currency, 0),
            )
            for currency in currencies
        )
        if any(balance.difference != 0 for balance in balances):
            issues.append(
                AccountingEntryIssue(
                    code="unbalanced_accounting_entry",
                    severity=AccountingEntryIssueSeverity.ERROR,
                    message="Debit and credit totals do not balance by currency",
                    line_ids=tuple(line.line_id for line in lines),
                ),
            )
        return ReconstructedAccountingEntry(
            entry_id=_entry_id(key),
            key=key,
            line_ids=tuple(line.line_id for line in lines),
            balances=balances,
            issues=tuple(issues),
        )


def _entry_key(entry: CanonicalLedgerEntry) -> AccountingEntryKey | None:
    if (
        entry.fiscal_year is None
        or entry.journal is None
        or entry.document_number is None
    ):
        return None
    return AccountingEntryKey(
        company_code=entry.company_code,
        fiscal_year=entry.fiscal_year,
        journal=entry.journal,
        document_number=entry.document_number,
    )


def _structural_issues(
    lines: tuple[CanonicalLedgerEntry, ...],
) -> list[AccountingEntryIssue]:
    issues: list[AccountingEntryIssue] = []
    posting_dates = {
        line.posting_date for line in lines if line.posting_date is not None
    }
    if len(posting_dates) > 1:
        issues.append(
            AccountingEntryIssue(
                code="multiple_posting_dates",
                severity=AccountingEntryIssueSeverity.ERROR,
                message="One accounting entry contains multiple posting dates",
                line_ids=tuple(line.line_id for line in lines),
            ),
        )
    currencies = {line.currency for line in lines if line.currency is not None}
    if len(currencies) > 1:
        issues.append(
            AccountingEntryIssue(
                code="multiple_document_currencies",
                severity=AccountingEntryIssueSeverity.ERROR,
                message="One accounting entry contains multiple document currencies",
                line_ids=tuple(line.line_id for line in lines),
            ),
        )
    line_numbers: dict[str, list[str]] = {}
    for line in lines:
        if line.line_number is not None:
            line_numbers.setdefault(line.line_number, []).append(line.line_id)
    for duplicate_lines in line_numbers.values():
        if len(duplicate_lines) > 1:
            issues.append(
                AccountingEntryIssue(
                    code="duplicate_accounting_line_number",
                    severity=AccountingEntryIssueSeverity.ERROR,
                    message="Accounting line number is duplicated within the entry",
                    line_ids=tuple(duplicate_lines),
                ),
            )
    for line in lines:
        if line.amount is None:
            issues.append(_line_issue("missing_amount", "Amount is missing", line))
        if line.currency is None:
            issues.append(_line_issue("missing_currency", "Currency is missing", line))
        if line.posting_key is None:
            issues.append(
                _line_issue("missing_posting_key", "Posting key is missing", line)
            )
        if line.amount is not None and line.amount < 0:
            issues.append(
                _line_issue(
                    "negative_source_amount_normalized",
                    "Negative source amount is classified by posting key "
                    "and absolute value",
                    line,
                ),
            )
    return issues


def _balance(
    currency: str,
    values: dict[str, Decimal | int] | None,
    excluded_line_count: int,
) -> AccountingEntryBalance:
    debit = Decimal(values["debit"]) if values is not None else Decimal("0")
    credit = Decimal(values["credit"]) if values is not None else Decimal("0")
    used = int(values["used"]) if values is not None else 0
    return AccountingEntryBalance(
        currency=currency,
        debit_total=debit,
        credit_total=credit,
        difference=debit - credit,
        used_line_count=used,
        excluded_line_count=excluded_line_count,
    )


def _line_issue(
    code: str,
    message: str,
    line: CanonicalLedgerEntry,
) -> AccountingEntryIssue:
    severity = (
        AccountingEntryIssueSeverity.WARNING
        if code == "negative_source_amount_normalized"
        else AccountingEntryIssueSeverity.ERROR
    )
    return AccountingEntryIssue(
        code=code,
        severity=severity,
        message=message,
        line_ids=(line.line_id,),
    )


def _entry_id(key: AccountingEntryKey) -> str:
    value = "|".join(
        (
            key.company_code or "UNSPECIFIED_COMPANY",
            str(key.fiscal_year),
            key.journal,
            key.document_number,
        ),
    )
    return sha256(value.encode("utf-8")).hexdigest()
