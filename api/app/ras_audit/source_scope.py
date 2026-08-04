from dataclasses import dataclass

from app.ledger_analysis.posting_key_rules import PostingKeyRule
from app.ras_audit.account_mapping import (
    RasLedgerAccountMapping,
    has_applicable_ras_payable_mapping,
)
from app.ras_audit.accounting_entry import AccountingEntryReconstructionReport
from app.ras_audit.normalization import LedgerNormalizationReport


@dataclass(frozen=True)
class RasUploadedSheetScope:
    is_complete: bool
    blocker_codes: tuple[str, ...]
    policy_version: str = "ras-uploaded-sheet-scope-v4"


def assess_uploaded_sheet_scope(
    *,
    normalization: LedgerNormalizationReport,
    reconstruction: AccountingEntryReconstructionReport,
    posting_key_rules: tuple[PostingKeyRule, ...],
    account_mappings: tuple[RasLedgerAccountMapping, ...],
) -> RasUploadedSheetScope:
    blockers: set[str] = set()
    if normalization.rejected_rows:
        blockers.add("rejected_source_rows")
    if reconstruction.ungrouped_line_ids:
        blockers.add("ungrouped_source_rows")
    if any(entry.company_code is None for entry in normalization.entries):
        blockers.add("missing_company_scope")
    if any(entry.line_number is None for entry in normalization.entries):
        blockers.add("missing_accounting_line_numbers")
    if any(entry.amount is None for entry in normalization.entries):
        blockers.add("missing_or_invalid_amounts")
    if any(entry.currency is None for entry in normalization.entries):
        blockers.add("missing_or_invalid_currencies")
    if any(entry.posting_date is None for entry in normalization.entries):
        blockers.add("missing_or_invalid_posting_dates")
    normalization_issue_codes = {issue.code for issue in normalization.issues}
    if "document_date_used_as_posting_date" in normalization_issue_codes:
        blockers.add("posting_date_is_document_date_proxy")
    if "document_type_used_as_journal" in normalization_issue_codes:
        blockers.add("journal_is_document_type_proxy")
    if any(
        entry.fiscal_year is None or entry.period is None
        for entry in normalization.entries
    ):
        blockers.add("missing_or_invalid_fiscal_periods")
    known_posting_keys = {rule.posting_key for rule in posting_key_rules}
    if any(
        entry.posting_key is None or entry.posting_key not in known_posting_keys
        for entry in normalization.entries
    ):
        blockers.add("missing_or_unknown_posting_keys")
    reconstruction_issue_codes = {
        issue.code
        for entry in reconstruction.entries
        for issue in entry.issues
    }
    if "duplicate_accounting_line_number" in reconstruction_issue_codes:
        blockers.add("duplicate_accounting_line_numbers")
    if "multiple_document_currencies" in reconstruction_issue_codes:
        blockers.add("conflicting_document_currencies")
    if "multiple_posting_dates" in reconstruction_issue_codes:
        blockers.add("conflicting_document_posting_dates")
    scopes = {
        (entry.posting_date, entry.company_code)
        for entry in normalization.entries
        if entry.posting_date is not None
    }
    if not scopes or any(
        not has_applicable_ras_payable_mapping(
            account_mappings,
            posting_date=posting_date,
            company_code=company_code,
        )
        for posting_date, company_code in scopes
    ):
        blockers.add("ras_payable_mapping_not_applicable")
    normalized_blockers = tuple(sorted(blockers))
    return RasUploadedSheetScope(
        is_complete=not normalized_blockers,
        blocker_codes=normalized_blockers,
    )
