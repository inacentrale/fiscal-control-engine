from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class RasAuditStatus(StrEnum):
    RAS_ACCOUNTED_COMPLIANT = "ras_accounted_compliant"
    RAS_AMOUNT_MISMATCH = "ras_accounted_amount_mismatch"
    RAS_NOT_FOUND_IN_LEDGER = "ras_not_found_in_ledger"
    APPLICABILITY_PROBABLE = "applicability_probable_to_confirm"
    INDETERMINATE = "indeterminate_missing_data"
    OUT_OF_SCOPE = "out_of_scope_justified"


class AuditEvidenceKind(StrEnum):
    LEDGER_LINE = "ledger_line"
    ACCOUNTING_ENTRY = "accounting_entry"
    LEGAL_RULE = "legal_rule"
    CALCULATION = "calculation"
    SCOPE_COMPLETENESS = "scope_completeness"
    MISSING_FACT = "missing_fact"


class AuditCapability(StrEnum):
    CANDIDATE_DETECTION = "candidate_detection"
    LEGAL_RULE_RESOLUTION = "legal_rule_resolution"
    THEORETICAL_CALCULATION = "theoretical_calculation"
    COUNTERPART_RECONCILIATION = "counterpart_reconciliation"


class LedgerField(StrEnum):
    COMPANY_CODE = "company_code"
    FISCAL_YEAR = "fiscal_year"
    PERIOD = "period"
    JOURNAL = "journal"
    DOCUMENT_NUMBER = "document_number"
    LINE_NUMBER = "line_number"
    POSTING_DATE = "posting_date"
    ACCOUNT_NUMBER = "account_number"
    PARTNER_ID = "partner_id"
    VENDOR_ID = "vendor_id"
    CUSTOMER_ID = "customer_id"
    LABEL = "label"
    POSTING_KEY = "posting_key"
    AMOUNT = "amount"
    CURRENCY = "currency"


@dataclass(frozen=True)
class LedgerSourceReference:
    file_name: str
    content_sha256: str
    sheet_name: str
    row_number: int

    def __post_init__(self) -> None:
        file_name = self.file_name.strip()
        sheet_name = self.sheet_name.strip()
        digest = self.content_sha256.strip().lower()
        if not file_name:
            raise ValueError("source file name is required")
        if not sheet_name:
            raise ValueError("source sheet name is required")
        if self.row_number < 1:
            raise ValueError("source row number must be positive")
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise ValueError("source SHA-256 must contain 64 hexadecimal characters")
        object.__setattr__(self, "file_name", file_name)
        object.__setattr__(self, "sheet_name", sheet_name)
        object.__setattr__(self, "content_sha256", digest)


@dataclass(frozen=True)
class SourceFieldValue:
    source_column: str
    source_value: object

    def __post_init__(self) -> None:
        source_column = self.source_column.strip()
        if not source_column:
            raise ValueError("source column is required")
        object.__setattr__(self, "source_column", source_column)


@dataclass(frozen=True)
class CanonicalLedgerEntry:
    line_id: str
    source: LedgerSourceReference
    company_code: str | None = None
    fiscal_year: int | None = None
    period: int | None = None
    journal: str | None = None
    document_number: str | None = None
    line_number: str | None = None
    posting_date: date | None = None
    account_number: str | None = None
    partner_id: str | None = None
    label: str | None = None
    posting_key: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    source_fields: tuple[SourceFieldValue, ...] = ()

    def __post_init__(self) -> None:
        line_id = self.line_id.strip()
        if not line_id:
            raise ValueError("ledger line id is required")
        if self.fiscal_year is not None and self.fiscal_year < 1:
            raise ValueError("fiscal year must be positive")
        if self.period is not None and not 1 <= self.period <= 16:
            raise ValueError("period must be between 1 and 16")
        posting_key = _optional_text(self.posting_key)
        if posting_key is not None and (
            len(posting_key) != 2 or not posting_key.isdigit()
        ):
            raise ValueError("posting key must contain two digits")
        if self.amount is not None and not self.amount.is_finite():
            raise ValueError("amount must be finite")

        object.__setattr__(self, "line_id", line_id)
        object.__setattr__(self, "company_code", _optional_text(self.company_code))
        object.__setattr__(self, "journal", _optional_text(self.journal))
        object.__setattr__(
            self,
            "document_number",
            _optional_text(self.document_number),
        )
        object.__setattr__(self, "line_number", _optional_text(self.line_number))
        object.__setattr__(
            self,
            "account_number",
            _optional_text(self.account_number),
        )
        object.__setattr__(self, "partner_id", _optional_text(self.partner_id))
        object.__setattr__(self, "label", _optional_text(self.label))
        object.__setattr__(self, "posting_key", posting_key)
        currency = _optional_text(self.currency)
        object.__setattr__(self, "currency", currency.upper() if currency else None)


@dataclass(frozen=True)
class AuditEvidence:
    evidence_id: str
    kind: AuditEvidenceKind
    description: str
    ledger_line_ids: tuple[str, ...] = ()
    source_url: str | None = None
    source_locator: str | None = None

    def __post_init__(self) -> None:
        evidence_id = self.evidence_id.strip()
        description = self.description.strip()
        if not evidence_id:
            raise ValueError("evidence id is required")
        if not description:
            raise ValueError("evidence description is required")
        if any(not line_id.strip() for line_id in self.ledger_line_ids):
            raise ValueError("evidence ledger line ids cannot be blank")
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "description", description)
        object.__setattr__(
            self,
            "source_url",
            _optional_text(self.source_url),
        )
        object.__setattr__(
            self,
            "source_locator",
            _optional_text(self.source_locator),
        )


_FIRM_STATUSES = frozenset(
    {
        RasAuditStatus.RAS_ACCOUNTED_COMPLIANT,
        RasAuditStatus.RAS_AMOUNT_MISMATCH,
        RasAuditStatus.RAS_NOT_FOUND_IN_LEDGER,
        RasAuditStatus.OUT_OF_SCOPE,
    },
)
_AMOUNT_COMPARISON_STATUSES = frozenset(
    {
        RasAuditStatus.RAS_ACCOUNTED_COMPLIANT,
        RasAuditStatus.RAS_AMOUNT_MISMATCH,
        RasAuditStatus.RAS_NOT_FOUND_IN_LEDGER,
    },
)
_REQUIRED_EVIDENCE_BY_STATUS: dict[RasAuditStatus, frozenset[AuditEvidenceKind]] = {
    RasAuditStatus.RAS_ACCOUNTED_COMPLIANT: frozenset(
        {
            AuditEvidenceKind.ACCOUNTING_ENTRY,
            AuditEvidenceKind.LEGAL_RULE,
            AuditEvidenceKind.CALCULATION,
            AuditEvidenceKind.SCOPE_COMPLETENESS,
        },
    ),
    RasAuditStatus.RAS_AMOUNT_MISMATCH: frozenset(
        {
            AuditEvidenceKind.ACCOUNTING_ENTRY,
            AuditEvidenceKind.LEGAL_RULE,
            AuditEvidenceKind.CALCULATION,
            AuditEvidenceKind.SCOPE_COMPLETENESS,
        },
    ),
    RasAuditStatus.RAS_NOT_FOUND_IN_LEDGER: frozenset(
        {
            AuditEvidenceKind.ACCOUNTING_ENTRY,
            AuditEvidenceKind.LEGAL_RULE,
            AuditEvidenceKind.CALCULATION,
            AuditEvidenceKind.SCOPE_COMPLETENESS,
        },
    ),
    RasAuditStatus.OUT_OF_SCOPE: frozenset(
        {AuditEvidenceKind.LEDGER_LINE, AuditEvidenceKind.LEGAL_RULE},
    ),
    RasAuditStatus.APPLICABILITY_PROBABLE: frozenset(
        {AuditEvidenceKind.LEDGER_LINE},
    ),
    RasAuditStatus.INDETERMINATE: frozenset(
        {AuditEvidenceKind.MISSING_FACT},
    ),
}


@dataclass(frozen=True)
class RasAuditFinding:
    candidate_id: str
    status: RasAuditStatus
    evidence: tuple[AuditEvidence, ...]
    basis_is_complete: bool
    expected_amount: Decimal | None = None
    recorded_amount: Decimal | None = None
    currency: str | None = None
    missing_facts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        candidate_id = self.candidate_id.strip()
        if not candidate_id:
            raise ValueError("candidate id is required")
        if self.status in _FIRM_STATUSES:
            if not self.basis_is_complete:
                raise ValueError("firm status requires a complete basis")
            if not self.evidence:
                raise ValueError("firm status requires evidence")
        evidence_kinds = {item.kind for item in self.evidence}
        missing_evidence = sorted(
            kind.value
            for kind in _REQUIRED_EVIDENCE_BY_STATUS[self.status] - evidence_kinds
        )
        if missing_evidence:
            raise ValueError(
                f"missing required evidence: {', '.join(missing_evidence)}"
            )
        if self.status in _AMOUNT_COMPARISON_STATUSES and (
            self.expected_amount is None
            or self.recorded_amount is None
            or not _optional_text(self.currency)
        ):
            raise ValueError(
                "amount comparison requires expected, recorded and currency"
            )
        for amount in (self.expected_amount, self.recorded_amount):
            if amount is not None and not amount.is_finite():
                raise ValueError("finding amounts must be finite")
        if any(not fact.strip() for fact in self.missing_facts):
            raise ValueError("missing fact names cannot be blank")
        if self.status is RasAuditStatus.INDETERMINATE and not self.missing_facts:
            raise ValueError("indeterminate status requires missing facts")
        object.__setattr__(self, "candidate_id", candidate_id)
        currency = _optional_text(self.currency)
        object.__setattr__(self, "currency", currency.upper() if currency else None)

    @property
    def difference(self) -> Decimal | None:
        if self.expected_amount is None or self.recorded_amount is None:
            return None
        return self.expected_amount - self.recorded_amount


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
