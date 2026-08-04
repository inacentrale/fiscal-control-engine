import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from pathlib import Path


class RasLegalRuleError(ValueError):
    pass


class RasLegalRuleStatus(StrEnum):
    ACTIVE_PROVISIONAL = "active_provisional"
    BLOCKED_MISSING_SCOPE_SOURCE = "blocked_missing_scope_source"


class RasCalculationMethod(StrEnum):
    FLAT_RATE = "flat_rate"
    IRF_PROGRESSIVE = "irf_progressive"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class RasLegalRule:
    rule_id: str
    version: str
    jurisdiction: str
    regime: str
    operation_type: str
    residence_status: str
    stable_establishment_status: str
    ifu_status: str
    beneficiary_type: str
    payer_type: str
    service_use_location: str
    treaty_override_status: str
    exemption_status: str
    minimum_amount: Decimal | None
    amount_currency: str | None
    calculation_method: RasCalculationMethod
    rate_percent: Decimal | None
    valid_from: date
    valid_to: date | None
    priority: int
    status: RasLegalRuleStatus
    required_facts: tuple[str, ...]
    scope_source_path: str
    scope_source_sha256: str
    scope_source_url: str
    scope_source_locator: str
    rate_source_path: str
    rate_source_sha256: str
    rate_source_url: str
    rate_source_locator: str
    source_assurance: str
    notes: str

    @property
    def is_active(self) -> bool:
        return self.status is RasLegalRuleStatus.ACTIVE_PROVISIONAL


def load_ras_legal_rules(
    path: Path,
    *,
    repository_root: Path,
) -> tuple[RasLegalRule, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames)
            rules = tuple(
                _parse_rule(row, row_number)
                for row_number, row in enumerate(reader, start=2)
            )
    except OSError as exc:
        raise RasLegalRuleError("RAS legal rule matrix cannot be read") from exc
    if not rules:
        raise RasLegalRuleError("RAS legal rule matrix is empty")
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise RasLegalRuleError("duplicate RAS legal rule id")
    for rule in rules:
        _verify_source(rule, repository_root)
    _validate_active_rule_overlaps(rules)
    return rules


def _parse_rule(row: dict[str, str | None], row_number: int) -> RasLegalRule:
    values = {key: (value or "").strip() for key, value in row.items()}
    required_values = _required_columns() - {
        "minimum_amount",
        "amount_currency",
        "rate_percent",
        "valid_to",
        "notes",
    }
    if any(not values[field] for field in required_values):
        raise RasLegalRuleError(f"incomplete RAS legal rule at row {row_number}")
    try:
        method = RasCalculationMethod(values["calculation_method"])
        status = RasLegalRuleStatus(values["activation_status"])
        minimum_amount = _optional_decimal(values["minimum_amount"])
        rate_percent = _optional_decimal(values["rate_percent"])
        valid_from = date.fromisoformat(values["valid_from"])
        valid_to = (
            date.fromisoformat(values["valid_to"])
            if values["valid_to"]
            else None
        )
        priority = int(values["priority"])
    except (ValueError, InvalidOperation) as exc:
        raise RasLegalRuleError(
            f"invalid RAS legal rule value at row {row_number}"
        ) from exc
    if valid_to is not None and valid_to < valid_from:
        raise RasLegalRuleError(f"invalid rule validity at row {row_number}")
    if priority < 0:
        raise RasLegalRuleError(f"invalid rule priority at row {row_number}")
    if status is RasLegalRuleStatus.ACTIVE_PROVISIONAL:
        if method is RasCalculationMethod.UNRESOLVED:
            raise RasLegalRuleError(
                f"active rule cannot be unresolved at row {row_number}"
            )
        if method is RasCalculationMethod.FLAT_RATE and rate_percent is None:
            raise RasLegalRuleError(
                f"flat rate is missing at row {row_number}"
            )
    if rate_percent is not None and not Decimal("0") <= rate_percent <= Decimal("100"):
        raise RasLegalRuleError(f"invalid rule rate at row {row_number}")
    scope_digest = _digest(values["scope_source_sha256"], row_number)
    rate_digest = _digest(values["rate_source_sha256"], row_number)
    required_facts = tuple(
        fact.strip() for fact in values["required_facts"].split(";") if fact.strip()
    )
    if not required_facts:
        raise RasLegalRuleError(f"required facts are missing at row {row_number}")
    return RasLegalRule(
        rule_id=values["rule_id"],
        version=values["version"],
        jurisdiction=values["jurisdiction"],
        regime=values["regime"],
        operation_type=values["operation_type"],
        residence_status=values["residence_status"],
        stable_establishment_status=values["stable_establishment_status"],
        ifu_status=values["ifu_status"],
        beneficiary_type=values["beneficiary_type"],
        payer_type=values["payer_type"],
        service_use_location=values["service_use_location"],
        treaty_override_status=values["treaty_override_status"],
        exemption_status=values["exemption_status"],
        minimum_amount=minimum_amount,
        amount_currency=values["amount_currency"] or None,
        calculation_method=method,
        rate_percent=rate_percent,
        valid_from=valid_from,
        valid_to=valid_to,
        priority=priority,
        status=status,
        required_facts=required_facts,
        scope_source_path=values["scope_source_path"],
        scope_source_sha256=scope_digest,
        scope_source_url=values["scope_source_url"],
        scope_source_locator=values["scope_source_locator"],
        rate_source_path=values["rate_source_path"],
        rate_source_sha256=rate_digest,
        rate_source_url=values["rate_source_url"],
        rate_source_locator=values["rate_source_locator"],
        source_assurance=values["source_assurance"],
        notes=values["notes"],
    )


def _verify_source(rule: RasLegalRule, repository_root: Path) -> None:
    _verify_source_file(
        repository_root,
        rule.scope_source_path,
        rule.scope_source_sha256,
        rule.rule_id,
        "scope",
    )
    _verify_source_file(
        repository_root,
        rule.rate_source_path,
        rule.rate_source_sha256,
        rule.rule_id,
        "rate",
    )


def _verify_source_file(
    repository_root: Path,
    relative_path: str,
    expected_digest: str,
    rule_id: str,
    evidence_kind: str,
) -> None:
    source_path = (repository_root / relative_path).resolve()
    root = repository_root.resolve()
    if root not in source_path.parents:
        raise RasLegalRuleError(f"rule source escapes repository: {rule_id}")
    try:
        digest = sha256(source_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise RasLegalRuleError(
            f"rule {evidence_kind} source cannot be read: {rule_id}"
        ) from exc
    if digest != expected_digest:
        raise RasLegalRuleError(
            f"rule {evidence_kind} source hash mismatch: {rule_id}"
        )


def _validate_active_rule_overlaps(rules: tuple[RasLegalRule, ...]) -> None:
    active = tuple(rule for rule in rules if rule.is_active)
    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            if (
                _condition_key(left) == _condition_key(right)
                and left.priority == right.priority
                and _periods_overlap(left, right)
            ):
                raise RasLegalRuleError("overlapping active RAS legal rules")


def _condition_key(rule: RasLegalRule) -> tuple[str, ...]:
    return (
        rule.jurisdiction,
        rule.regime,
        rule.operation_type,
        rule.residence_status,
        rule.stable_establishment_status,
        rule.ifu_status,
        rule.beneficiary_type,
        rule.payer_type,
        rule.service_use_location,
        rule.treaty_override_status,
        rule.exemption_status,
    )


def _periods_overlap(left: RasLegalRule, right: RasLegalRule) -> bool:
    return left.valid_from <= (right.valid_to or date.max) and right.valid_from <= (
        left.valid_to or date.max
    )


def _optional_decimal(value: str) -> Decimal | None:
    return Decimal(value) if value else None


def _digest(value: str, row_number: int) -> str:
    digest = value.lower()
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise RasLegalRuleError(f"invalid source hash at row {row_number}")
    return digest


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    missing = _required_columns() - set(fieldnames or ())
    if missing:
        raise RasLegalRuleError(
            f"missing legal rule columns: {', '.join(sorted(missing))}"
        )


def _required_columns() -> set[str]:
    return {
        "rule_id", "version", "jurisdiction", "regime", "operation_type",
        "residence_status", "stable_establishment_status", "ifu_status",
        "beneficiary_type", "payer_type", "service_use_location",
        "treaty_override_status", "exemption_status", "minimum_amount",
        "amount_currency", "calculation_method", "rate_percent", "valid_from",
        "valid_to", "priority", "activation_status", "required_facts",
        "scope_source_path", "scope_source_sha256", "scope_source_url",
        "scope_source_locator", "rate_source_path", "rate_source_sha256",
        "rate_source_url", "rate_source_locator",
        "source_assurance", "notes",
    }
