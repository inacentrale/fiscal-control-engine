from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class ValidationLayer(StrEnum):
    STRUCTURE = "structure"
    COMPLETENESS = "completeness"
    ARITHMETIC = "arithmetic"
    FISCAL = "fiscal"
    HISTORICAL = "historical"
    RECONCILIATION = "reconciliation"
    STATISTICAL = "statistical"
    SUPPORTING_DOCUMENTS = "supporting_documents"
    PAYMENT_RECONCILIATION = "payment_reconciliation"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_EVALUATED = "not_evaluated"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class OverallValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class VatValidationRule:
    rule_id: str
    version: str
    layer: ValidationLayer
    target_line: str
    target_field: str
    operator: str
    operand_lines: tuple[str, ...]
    expected_value: Decimal | None
    tolerance: Decimal
    valid_from: date | None
    valid_to: date | None
    source_url: str
    source_locator: str


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    layer: ValidationLayer
    status: ValidationStatus
    severity: ValidationSeverity
    message: str
    source_url: str | None = None
    source_locator: str | None = None
    expected_value: Decimal | None = None
    actual_value: Decimal | None = None
    difference: Decimal | None = None
    expected_date: date | None = None
    actual_date: date | None = None
    affected_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaxDeclarationValidationReport:
    overall_status: OverallValidationStatus
    checks: tuple[ValidationCheck, ...]
