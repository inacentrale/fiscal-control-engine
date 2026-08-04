import csv
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path


class RasLedgerAccountRole(StrEnum):
    EXPENSE_CANDIDATE = "expense_candidate"
    RAS_PAYABLE = "ras_payable"


class AccountMatchType(StrEnum):
    EXACT = "exact"
    PREFIX = "prefix"


class AccountNormalSide(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class RasLedgerAccountMappingError(ValueError):
    pass


@dataclass(frozen=True)
class RasLedgerAccountMapping:
    mapping_id: str
    version: str
    role: RasLedgerAccountRole
    match_type: AccountMatchType
    account_pattern: str
    normal_side: AccountNormalSide
    company_code: str | None
    valid_from: date | None
    valid_to: date | None
    organization_reference: str

    def matches(
        self,
        account_number: str,
        *,
        posting_date: date,
        company_code: str | None,
    ) -> bool:
        if self.valid_from is not None and posting_date < self.valid_from:
            return False
        if self.valid_to is not None and posting_date > self.valid_to:
            return False
        if self.company_code is not None and self.company_code != company_code:
            return False
        if self.match_type is AccountMatchType.EXACT:
            return account_number == self.account_pattern
        return account_number.startswith(self.account_pattern)


def load_ras_ledger_account_mappings(
    path: Path,
) -> tuple[RasLedgerAccountMapping, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or not _required_columns().issubset(
                reader.fieldnames
            ):
                raise RasLedgerAccountMappingError(
                    "invalid RAS ledger account mapping columns"
                )
            mappings = tuple(
                _parse_mapping(row, row_number)
                for row_number, row in enumerate(reader, start=2)
            )
    except OSError as exc:
        raise RasLedgerAccountMappingError(
            "RAS ledger account mapping cannot be read"
        ) from exc
    if not mappings:
        raise RasLedgerAccountMappingError("RAS ledger account mapping is empty")
    if len({mapping.mapping_id for mapping in mappings}) != len(mappings):
        raise RasLedgerAccountMappingError("duplicate RAS ledger mapping id")
    _validate_overlaps(mappings)
    return mappings


def matching_account_mappings(
    mappings: tuple[RasLedgerAccountMapping, ...],
    account_number: str,
    *,
    posting_date: date,
    company_code: str | None,
) -> tuple[RasLedgerAccountMapping, ...]:
    normalized_account = account_number.strip()
    if not normalized_account or not normalized_account.isdigit():
        return ()
    normalized_company = company_code.strip() if company_code else None
    return tuple(
        mapping
        for mapping in mappings
        if mapping.matches(
            normalized_account,
            posting_date=posting_date,
            company_code=normalized_company,
        )
    )


def best_account_mapping(
    mappings: tuple[RasLedgerAccountMapping, ...],
    account_number: str,
    *,
    role: RasLedgerAccountRole,
    posting_date: date,
    company_code: str | None,
) -> RasLedgerAccountMapping | None:
    matches = tuple(
        mapping
        for mapping in matching_account_mappings(
            mappings,
            account_number,
            posting_date=posting_date,
            company_code=company_code,
        )
        if mapping.role is role
    )
    if not matches:
        return None
    return max(
        matches,
        key=lambda mapping: (
            mapping.match_type is AccountMatchType.EXACT,
            len(mapping.account_pattern),
        ),
    )


def has_ras_payable_mapping(
    mappings: tuple[RasLedgerAccountMapping, ...],
) -> bool:
    return any(mapping.role is RasLedgerAccountRole.RAS_PAYABLE for mapping in mappings)


def has_expense_candidate_mapping(
    mappings: tuple[RasLedgerAccountMapping, ...],
) -> bool:
    return any(
        mapping.role is RasLedgerAccountRole.EXPENSE_CANDIDATE
        for mapping in mappings
    )


def has_applicable_ras_payable_mapping(
    mappings: tuple[RasLedgerAccountMapping, ...],
    *,
    posting_date: date,
    company_code: str | None,
) -> bool:
    return any(
        mapping.role is RasLedgerAccountRole.RAS_PAYABLE
        and (mapping.valid_from is None or posting_date >= mapping.valid_from)
        and (mapping.valid_to is None or posting_date <= mapping.valid_to)
        and (
            mapping.company_code is None or mapping.company_code == company_code
        )
        for mapping in mappings
    )


def _parse_mapping(
    row: dict[str, str | None],
    row_number: int,
) -> RasLedgerAccountMapping:
    values = {key: (value or "").strip() for key, value in row.items()}
    for field in (
        "mapping_id",
        "version",
        "role",
        "match_type",
        "account_pattern",
        "normal_side",
        "organization_reference",
    ):
        if not values.get(field):
            raise RasLedgerAccountMappingError(
                f"incomplete RAS ledger mapping at row {row_number}"
            )
    account_pattern = values["account_pattern"]
    if not account_pattern.isdigit():
        raise RasLedgerAccountMappingError(
            f"account pattern must be numeric at row {row_number}"
        )
    try:
        role = RasLedgerAccountRole(values["role"])
        match_type = AccountMatchType(values["match_type"])
        normal_side = AccountNormalSide(values["normal_side"])
        valid_from = _optional_date(values.get("valid_from", ""))
        valid_to = _optional_date(values.get("valid_to", ""))
    except ValueError as exc:
        raise RasLedgerAccountMappingError(
            f"invalid RAS ledger mapping value at row {row_number}"
        ) from exc
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise RasLedgerAccountMappingError(
            f"invalid RAS ledger mapping validity at row {row_number}"
        )
    company_code = values.get("company_code") or None
    return RasLedgerAccountMapping(
        mapping_id=values["mapping_id"],
        version=values["version"],
        role=role,
        match_type=match_type,
        account_pattern=account_pattern,
        normal_side=normal_side,
        company_code=company_code,
        valid_from=valid_from,
        valid_to=valid_to,
        organization_reference=values["organization_reference"],
    )


def _validate_overlaps(
    mappings: tuple[RasLedgerAccountMapping, ...],
) -> None:
    for index, left in enumerate(mappings):
        for right in mappings[index + 1 :]:
            if (
                left.role is right.role
                and left.match_type is right.match_type
                and left.account_pattern == right.account_pattern
                and left.company_code == right.company_code
                and _periods_overlap(left, right)
            ):
                raise RasLedgerAccountMappingError(
                    "overlapping RAS ledger account mappings"
                )


def _periods_overlap(
    left: RasLedgerAccountMapping,
    right: RasLedgerAccountMapping,
) -> bool:
    left_start = left.valid_from or date.min
    left_end = left.valid_to or date.max
    right_start = right.valid_from or date.min
    right_end = right.valid_to or date.max
    return left_start <= right_end and right_start <= left_end


def _optional_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def _required_columns() -> set[str]:
    return {
        "mapping_id",
        "version",
        "role",
        "match_type",
        "account_pattern",
        "normal_side",
        "company_code",
        "valid_from",
        "valid_to",
        "organization_reference",
    }
