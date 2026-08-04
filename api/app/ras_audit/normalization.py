import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import isfinite

from app.ras_audit.account_mapping import (
    RasLedgerAccountMapping,
    has_applicable_ras_payable_mapping,
)
from app.ras_audit.domain import (
    CanonicalLedgerEntry,
    LedgerField,
    LedgerSourceReference,
    SourceFieldValue,
)
from app.ras_audit.readiness import (
    LedgerReadinessInput,
    LedgerReadinessReport,
    assess_ledger_readiness,
)


@dataclass(frozen=True)
class LedgerColumnBinding:
    field: LedgerField
    source_column: str

    def __post_init__(self) -> None:
        source_column = self.source_column.strip()
        if not source_column:
            raise ValueError("source column is required")
        object.__setattr__(self, "source_column", source_column)


@dataclass(frozen=True)
class LedgerNormalizationRequest:
    source_file_name: str
    content_sha256: str
    sheet_name: str
    first_data_row: int
    source_columns: tuple[str, ...]
    rows: tuple[Mapping[str, object], ...]
    bindings: tuple[LedgerColumnBinding, ...]
    known_posting_keys: frozenset[str] = frozenset()
    source_scope_complete: bool | None = None
    ras_account_mappings: tuple[RasLedgerAccountMapping, ...] = ()
    default_company_code: str | None = None

    def __post_init__(self) -> None:
        if not self.source_file_name.strip():
            raise ValueError("source file name is required")
        if not self.sheet_name.strip():
            raise ValueError("sheet name is required")
        if self.first_data_row < 1:
            raise ValueError("first data row must be positive")
        if self.default_company_code is not None:
            normalized_company = self.default_company_code.strip()
            if not normalized_company:
                raise ValueError("default company code cannot be blank")
            object.__setattr__(self, "default_company_code", normalized_company)


@dataclass(frozen=True)
class LedgerNormalizationIssue:
    line_id: str
    row_number: int
    field: LedgerField
    code: str
    message: str


@dataclass(frozen=True)
class RejectedLedgerRow:
    row_number: int
    reason_code: str
    message: str


@dataclass(frozen=True)
class LedgerNormalizationReport:
    source_file_name: str
    content_sha256: str
    sheet_name: str
    bindings: tuple[LedgerColumnBinding, ...]
    entries: tuple[CanonicalLedgerEntry, ...]
    rejected_rows: tuple[RejectedLedgerRow, ...]
    issues: tuple[LedgerNormalizationIssue, ...]
    readiness: LedgerReadinessReport


class LedgerNormalizer:
    def normalize(
        self,
        request: LedgerNormalizationRequest,
    ) -> LedgerNormalizationReport:
        _validate_bindings(request.bindings, request.source_columns)
        entries: list[CanonicalLedgerEntry] = []
        rejected_rows: list[RejectedLedgerRow] = []
        issues: list[LedgerNormalizationIssue] = []
        unknown_posting_key_found = False

        for offset, row in enumerate(request.rows):
            row_number = request.first_data_row + offset
            if _is_structural_blank(row, request.bindings):
                rejected_rows.append(
                    RejectedLedgerRow(
                        row_number=row_number,
                        reason_code="structural_blank_row",
                        message="No mapped ledger value is present on this row",
                    ),
                )
                continue
            entry, row_issues = _normalize_row(request, row, row_number)
            entries.append(entry)
            issues.extend(row_issues)
            unknown_posting_key_found = unknown_posting_key_found or any(
                issue.code == "unknown_posting_key" for issue in row_issues
            )

        available_fields = frozenset(binding.field for binding in request.bindings)
        posting_key_is_mapped = LedgerField.POSTING_KEY in available_fields
        posting_keys_complete = (
            posting_key_is_mapped
            and bool(request.known_posting_keys)
            and not unknown_posting_key_found
            and not any(issue.field is LedgerField.POSTING_KEY for issue in issues)
        )
        readiness = assess_ledger_readiness(
            LedgerReadinessInput(
                available_fields=available_fields,
                source_scope_complete=request.source_scope_complete,
                ras_account_mapping_available=_ras_mapping_covers_scope(
                    entries,
                    request.ras_account_mappings,
                ),
                posting_keys_complete=posting_keys_complete,
            ),
        )
        return LedgerNormalizationReport(
            source_file_name=request.source_file_name.strip(),
            content_sha256=request.content_sha256.strip().lower(),
            sheet_name=request.sheet_name.strip(),
            bindings=request.bindings,
            entries=tuple(entries),
            rejected_rows=tuple(rejected_rows),
            issues=tuple(issues),
            readiness=readiness,
        )


def _normalize_row(
    request: LedgerNormalizationRequest,
    row: Mapping[str, object],
    row_number: int,
) -> tuple[CanonicalLedgerEntry, tuple[LedgerNormalizationIssue, ...]]:
    line_id = f"{request.sheet_name.strip()}:{row_number}"
    values = {
        binding.field: row.get(binding.source_column)
        for binding in request.bindings
    }
    issues: list[LedgerNormalizationIssue] = []
    source_column_by_field = {
        binding.field: _normalized_column_name(binding.source_column)
        for binding in request.bindings
    }

    if source_column_by_field.get(LedgerField.POSTING_DATE) == "date piece":
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.POSTING_DATE,
                "document_date_used_as_posting_date",
                "Document date is only a proxy for the accounting posting date",
            ),
        )
    if source_column_by_field.get(LedgerField.JOURNAL) == "type de piece":
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.JOURNAL,
                "document_type_used_as_journal",
                "Document type is only a proxy for the accounting journal",
            ),
        )

    fiscal_year = _integer(values.get(LedgerField.FISCAL_YEAR))
    if _has_value(values.get(LedgerField.FISCAL_YEAR)) and (
        fiscal_year is None or fiscal_year < 1
    ):
        fiscal_year = None
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.FISCAL_YEAR,
                "invalid_fiscal_year",
                "Fiscal year must be a positive integer",
            ),
        )
    period = _integer(values.get(LedgerField.PERIOD))
    if _has_value(values.get(LedgerField.PERIOD)) and (
        period is None or not 1 <= period <= 16
    ):
        period = None
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.PERIOD,
                "invalid_period",
                "Period must be an integer between 1 and 16",
            ),
        )

    amount = _amount(values.get(LedgerField.AMOUNT))
    if _has_value(values.get(LedgerField.AMOUNT)) and amount is None:
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.AMOUNT,
                "invalid_amount",
                "Amount cannot be normalized deterministically",
            ),
        )
    posting_date = _posting_date(values.get(LedgerField.POSTING_DATE))
    if _has_value(values.get(LedgerField.POSTING_DATE)) and posting_date is None:
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.POSTING_DATE,
                "invalid_posting_date",
                "Posting date cannot be normalized deterministically",
            ),
        )
    posting_key = _identifier(values.get(LedgerField.POSTING_KEY))
    if posting_key is not None and posting_key.isdigit() and len(posting_key) == 1:
        posting_key = posting_key.zfill(2)
    if posting_key is not None and (
        len(posting_key) != 2 or not posting_key.isdigit()
    ):
        posting_key = None
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.POSTING_KEY,
                "invalid_posting_key",
                "Posting key must contain two digits",
            ),
        )
    elif (
        posting_key is not None
        and request.known_posting_keys
        and posting_key not in request.known_posting_keys
    ):
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.POSTING_KEY,
                "unknown_posting_key",
                "Posting key is absent from the supplied reference",
            ),
        )
    currency = _currency(values.get(LedgerField.CURRENCY))
    if _has_value(values.get(LedgerField.CURRENCY)) and currency is None:
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.CURRENCY,
                "invalid_currency",
                "Currency must contain a three-letter alphabetic code",
            ),
        )

    partner_id = _identifier(values.get(LedgerField.PARTNER_ID))
    vendor_id = _identifier(values.get(LedgerField.VENDOR_ID))
    customer_id = _identifier(values.get(LedgerField.CUSTOMER_ID))
    specialized_partners = {value for value in (vendor_id, customer_id) if value}
    if partner_id is None and len(specialized_partners) == 1:
        partner_id = next(iter(specialized_partners))
    elif partner_id is None and len(specialized_partners) > 1:
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.PARTNER_ID,
                "conflicting_vendor_customer",
                "Vendor and customer identifiers differ on the same row",
            ),
        )
    elif partner_id is not None and any(
        specialized != partner_id for specialized in specialized_partners
    ):
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.PARTNER_ID,
                "conflicting_generic_partner",
                "Generic partner conflicts with vendor or customer identifier",
            ),
        )
        partner_id = None

    company_code = _identifier(values.get(LedgerField.COMPANY_CODE))
    if company_code is None and request.default_company_code is not None:
        company_code = request.default_company_code
        issues.append(
            _issue(
                line_id,
                row_number,
                LedgerField.COMPANY_CODE,
                "company_code_from_organization_config",
                "Company scope comes from explicit organization configuration",
            ),
        )

    entry = CanonicalLedgerEntry(
        line_id=line_id,
        source=LedgerSourceReference(
            file_name=request.source_file_name,
            content_sha256=request.content_sha256,
            sheet_name=request.sheet_name,
            row_number=row_number,
        ),
        company_code=company_code,
        fiscal_year=fiscal_year,
        period=period,
        journal=_text(values.get(LedgerField.JOURNAL)),
        document_number=_identifier(values.get(LedgerField.DOCUMENT_NUMBER)),
        line_number=(
            _identifier(values.get(LedgerField.LINE_NUMBER)) or str(row_number)
        ),
        posting_date=posting_date,
        account_number=_identifier(values.get(LedgerField.ACCOUNT_NUMBER)),
        partner_id=partner_id,
        label=_text(values.get(LedgerField.LABEL)),
        posting_key=posting_key,
        amount=amount,
        currency=currency,
        source_fields=tuple(
            SourceFieldValue(
                source_column=binding.source_column,
                source_value=row.get(binding.source_column),
            )
            for binding in request.bindings
        ),
    )
    return entry, tuple(issues)


def _validate_bindings(
    bindings: tuple[LedgerColumnBinding, ...],
    source_columns: tuple[str, ...],
) -> None:
    if len(set(source_columns)) != len(source_columns):
        raise ValueError("source columns must be unique")
    available_columns = set(source_columns)
    seen_fields: set[LedgerField] = set()
    seen_columns: set[str] = set()
    for binding in bindings:
        if binding.field in seen_fields:
            raise ValueError(f"ledger field is bound more than once: {binding.field}")
        if binding.source_column in seen_columns:
            raise ValueError(
                "source column cannot map to multiple ledger fields: "
                f"{binding.source_column}"
            )
        if binding.source_column not in available_columns:
            raise ValueError(
                f"mapped source column is unavailable: {binding.source_column}"
            )
        seen_fields.add(binding.field)
        seen_columns.add(binding.source_column)


def _is_structural_blank(
    row: Mapping[str, object],
    bindings: tuple[LedgerColumnBinding, ...],
) -> bool:
    return not any(_has_value(row.get(binding.source_column)) for binding in bindings)


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return not (isinstance(value, float) and not isfinite(value))


def _text(value: object) -> str | None:
    if not _has_value(value):
        return None
    normalized = str(value).strip()
    return normalized or None


def _identifier(value: object) -> str | None:
    if not _has_value(value) or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f") if value % 1 else format(value, ".0f")
    if isinstance(value, float):
        if not isfinite(value):
            return None
        return format(value, ".0f") if value.is_integer() else str(value)
    return _text(value)


def _integer(value: object) -> int | None:
    identifier = _identifier(value)
    if identifier is None:
        return None
    try:
        return int(identifier)
    except ValueError:
        return None


def _amount(value: object) -> Decimal | None:
    if not _has_value(value) or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value if value.is_finite() else None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not isfinite(value):
            return None
        return Decimal(str(value))
    normalized = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        return None
    if "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        result = Decimal(normalized)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def _currency(value: object) -> str | None:
    normalized = _text(value)
    if normalized is None:
        return None
    normalized = normalized.upper()
    if len(normalized) != 3 or not normalized.isascii() or not normalized.isalpha():
        return None
    return normalized


def _normalized_column_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.casefold().split())


def _posting_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    normalized = _text(value)
    if normalized is None:
        return None
    for parser in (
        date.fromisoformat,
        lambda raw: datetime.strptime(raw, "%d/%m/%Y").date(),
    ):
        try:
            return parser(normalized)
        except ValueError:
            continue
    return None


def _issue(
    line_id: str,
    row_number: int,
    field: LedgerField,
    code: str,
    message: str,
) -> LedgerNormalizationIssue:
    return LedgerNormalizationIssue(
        line_id=line_id,
        row_number=row_number,
        field=field,
        code=code,
        message=message,
    )


def _ras_mapping_covers_scope(
    entries: list[CanonicalLedgerEntry],
    mappings: tuple[RasLedgerAccountMapping, ...],
) -> bool:
    scopes: set[tuple[str | None, date]] = set()
    for entry in entries:
        if entry.posting_date is None:
            return False
        scopes.add((entry.company_code, entry.posting_date))
    if not scopes:
        return False
    return all(
        has_applicable_ras_payable_mapping(
            mappings,
            company_code=company_code,
            posting_date=posting_date,
        )
        for company_code, posting_date in scopes
    )
