import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from app.ras_audit.legal_rules import RasCalculationMethod, RasLegalRule
from app.ras_audit.rule_resolution import (
    RasLegalFact,
    RasRuleResolution,
    RasRuleResolutionStatus,
)


class RasCalculationError(ValueError):
    pass


class RasTheoreticalCalculationStatus(StrEnum):
    CALCULATED_PROVISIONAL = "calculated_provisional"
    EXEMPTION_PROVISIONAL = "exemption_provisional"
    NOT_CALCULABLE = "not_calculable"


@dataclass(frozen=True)
class RasCalculationParameter:
    parameter_id: str
    version: str
    calculation_method: RasCalculationMethod
    parameter_name: str
    value: Decimal
    currency: str
    valid_from: date
    valid_to: date | None
    source_path: str
    source_sha256: str
    source_url: str
    source_locator: str
    source_assurance: str


@dataclass(frozen=True)
class RasCalculationStep:
    step: str
    expression: str
    result: Decimal


@dataclass(frozen=True)
class RasTheoreticalCalculation:
    status: RasTheoreticalCalculationStatus
    rule_id: str | None
    rule_version: str | None
    base_fact_name: str | None
    base_amount: Decimal | None
    expected_amount: Decimal | None
    currency: str | None
    calculation_method: str | None
    rate_percent: Decimal | None
    steps: tuple[RasCalculationStep, ...]
    parameter_versions: tuple[str, ...]
    source_locators: tuple[str, ...]
    rounding_policy: str
    reason: str | None


@dataclass(frozen=True)
class RasTheoreticalCalculationToolReport:
    resolution: RasRuleResolution
    calculation: RasTheoreticalCalculation


def load_ras_calculation_parameters(
    path: Path,
    *,
    repository_root: Path,
) -> tuple[RasCalculationParameter, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames)
            parameters = tuple(
                _parse_parameter(row, row_number)
                for row_number, row in enumerate(reader, start=2)
            )
    except OSError as exc:
        raise RasCalculationError("RAS calculation parameters cannot be read") from exc
    if not parameters:
        raise RasCalculationError("RAS calculation parameters are empty")
    if len({item.parameter_id for item in parameters}) != len(parameters):
        raise RasCalculationError("duplicate RAS calculation parameter id")
    _validate_parameter_overlaps(parameters)
    for parameter in parameters:
        _verify_parameter_source(parameter, repository_root)
    return parameters


class RasTheoreticalCalculator:
    def __init__(
        self,
        *,
        rules: tuple[RasLegalRule, ...],
        parameters: tuple[RasCalculationParameter, ...],
    ) -> None:
        self._rules = {rule.rule_id: rule for rule in rules}
        self._parameters = parameters

    def calculate(
        self,
        *,
        transaction_date: date,
        facts: tuple[RasLegalFact, ...],
        resolution: RasRuleResolution,
    ) -> RasTheoreticalCalculation:
        if resolution.status not in {
            RasRuleResolutionStatus.RESOLVED_PROVISIONAL,
            RasRuleResolutionStatus.EXEMPTION_PROVISIONAL,
        }:
            return _not_calculable("legal_rule_is_not_resolved")
        if resolution.rule_id is None:
            return _not_calculable("resolved_rule_id_is_missing")
        rule = self._rules.get(resolution.rule_id)
        if rule is None or rule.version != resolution.rule_version:
            return _not_calculable("resolved_rule_version_is_unavailable")
        fact_values = {fact.name: fact.value for fact in facts}
        currency = fact_values.get("currency")
        if currency is None:
            return _not_calculable("currency_is_missing")
        if rule.amount_currency is not None and currency != rule.amount_currency:
            return _not_calculable("currency_mismatch")
        base_fact_name = _base_fact_name(rule)
        if base_fact_name is None or base_fact_name not in fact_values:
            return _not_calculable("calculation_base_is_missing")
        base_amount = Decimal(fact_values[base_fact_name])

        if resolution.status is RasRuleResolutionStatus.EXEMPTION_PROVISIONAL:
            return RasTheoreticalCalculation(
                status=RasTheoreticalCalculationStatus.EXEMPTION_PROVISIONAL,
                rule_id=rule.rule_id,
                rule_version=rule.version,
                base_fact_name=base_fact_name,
                base_amount=base_amount,
                expected_amount=Decimal("0"),
                currency=currency,
                calculation_method=rule.calculation_method.value,
                rate_percent=Decimal("0"),
                steps=(
                    RasCalculationStep(
                        step="exemption",
                        expression="verified exemption => 0",
                        result=Decimal("0"),
                    ),
                ),
                parameter_versions=(),
                source_locators=(rule.scope_source_locator,),
                rounding_policy="none_exact_decimal",
                reason=None,
            )
        if base_fact_name == "tax_base_amount" and "payment_amount" in fact_values:
            payment_amount = Decimal(fact_values["payment_amount"])
            if payment_amount < base_amount:
                return _not_calculable(
                    "partial_payment_tax_base_allocation_unresolved"
                )
            if payment_amount > base_amount:
                return _not_calculable("payment_amount_exceeds_tax_base")
        if rule.calculation_method is RasCalculationMethod.FLAT_RATE:
            return _flat_rate_calculation(rule, base_fact_name, base_amount, currency)
        if rule.calculation_method is RasCalculationMethod.IRF_PROGRESSIVE:
            return self._irf_calculation(
                rule,
                base_fact_name,
                base_amount,
                currency,
                transaction_date,
            )
        return _not_calculable("calculation_method_is_unresolved")

    def _irf_calculation(
        self,
        rule: RasLegalRule,
        base_fact_name: str,
        gross_rent: Decimal,
        currency: str,
        transaction_date: date,
    ) -> RasTheoreticalCalculation:
        parameters = {
            item.parameter_name: item
            for item in self._parameters
            if item.calculation_method is RasCalculationMethod.IRF_PROGRESSIVE
            and item.currency == currency
            and item.valid_from <= transaction_date
            and (item.valid_to is None or transaction_date <= item.valid_to)
        }
        required = {
            "abatement_percent",
            "first_band_limit",
            "first_band_rate_percent",
            "excess_rate_percent",
        }
        if parameters.keys() < required:
            return _not_calculable("calculation_parameters_are_incomplete")
        abatement = parameters["abatement_percent"].value
        limit = parameters["first_band_limit"].value
        first_rate = parameters["first_band_rate_percent"].value
        excess_rate = parameters["excess_rate_percent"].value
        net = gross_rent * (Decimal("100") - abatement) / Decimal("100")
        first_band = min(net, limit)
        excess_band = max(net - limit, Decimal("0"))
        first_tax = first_band * first_rate / Decimal("100")
        excess_tax = excess_band * excess_rate / Decimal("100")
        expected = first_tax + excess_tax
        ordered = tuple(parameters[name] for name in sorted(required))
        return RasTheoreticalCalculation(
            status=RasTheoreticalCalculationStatus.CALCULATED_PROVISIONAL,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            base_fact_name=base_fact_name,
            base_amount=gross_rent,
            expected_amount=expected,
            currency=currency,
            calculation_method=rule.calculation_method.value,
            rate_percent=None,
            steps=(
                RasCalculationStep(
                    step="net_taxable_rent",
                    expression="gross * (100 - abatement_percent) / 100",
                    result=net,
                ),
                RasCalculationStep(
                    step="first_band_tax",
                    expression="min(net, first_band_limit) * first_band_rate / 100",
                    result=first_tax,
                ),
                RasCalculationStep(
                    step="excess_band_tax",
                    expression="max(net - first_band_limit, 0) * excess_rate / 100",
                    result=excess_tax,
                ),
            ),
            parameter_versions=tuple(item.version for item in ordered),
            source_locators=tuple(item.source_locator for item in ordered),
            rounding_policy="none_exact_decimal_source_rounding_unavailable",
            reason=None,
        )


def _flat_rate_calculation(
    rule: RasLegalRule,
    base_fact_name: str,
    base_amount: Decimal,
    currency: str,
) -> RasTheoreticalCalculation:
    if rule.rate_percent is None:
        return _not_calculable("flat_rate_is_missing")
    expected = base_amount * rule.rate_percent / Decimal("100")
    return RasTheoreticalCalculation(
        status=RasTheoreticalCalculationStatus.CALCULATED_PROVISIONAL,
        rule_id=rule.rule_id,
        rule_version=rule.version,
        base_fact_name=base_fact_name,
        base_amount=base_amount,
        expected_amount=expected,
        currency=currency,
        calculation_method=rule.calculation_method.value,
        rate_percent=rule.rate_percent,
        steps=(
            RasCalculationStep(
                step="flat_rate",
                expression="base * rate_percent / 100",
                result=expected,
            ),
        ),
        parameter_versions=(),
        source_locators=(rule.rate_source_locator,),
        rounding_policy="none_exact_decimal_source_rounding_unavailable",
        reason=None,
    )


def _base_fact_name(rule: RasLegalRule) -> str | None:
    return next(
        (name for name in rule.required_facts if name in {
            "tax_base_amount", "payment_amount", "gross_rent_excluding_vat"
        }),
        None,
    )


def _not_calculable(reason: str) -> RasTheoreticalCalculation:
    return RasTheoreticalCalculation(
        status=RasTheoreticalCalculationStatus.NOT_CALCULABLE,
        rule_id=None,
        rule_version=None,
        base_fact_name=None,
        base_amount=None,
        expected_amount=None,
        currency=None,
        calculation_method=None,
        rate_percent=None,
        steps=(),
        parameter_versions=(),
        source_locators=(),
        rounding_policy="not_applicable",
        reason=reason,
    )


def _parse_parameter(
    row: dict[str, str | None],
    row_number: int,
) -> RasCalculationParameter:
    values = {key: (value or "").strip() for key, value in row.items()}
    if any(not values[field] for field in _required_columns() - {"valid_to"}):
        raise RasCalculationError(
            f"incomplete RAS calculation parameter at row {row_number}"
        )
    try:
        value = Decimal(values["value"])
        method = RasCalculationMethod(values["calculation_method"])
        valid_from = date.fromisoformat(values["valid_from"])
        valid_to = (
            date.fromisoformat(values["valid_to"])
            if values["valid_to"]
            else None
        )
    except (ValueError, InvalidOperation) as exc:
        raise RasCalculationError(
            f"invalid RAS calculation parameter at row {row_number}"
        ) from exc
    if not value.is_finite() or value < 0:
        raise RasCalculationError(f"invalid parameter value at row {row_number}")
    if valid_to is not None and valid_to < valid_from:
        raise RasCalculationError(f"invalid parameter validity at row {row_number}")
    digest = values["source_sha256"].lower()
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise RasCalculationError(f"invalid parameter source hash at row {row_number}")
    return RasCalculationParameter(
        parameter_id=values["parameter_id"],
        version=values["version"],
        calculation_method=method,
        parameter_name=values["parameter_name"],
        value=value,
        currency=values["currency"].upper(),
        valid_from=valid_from,
        valid_to=valid_to,
        source_path=values["source_path"],
        source_sha256=digest,
        source_url=values["source_url"],
        source_locator=values["source_locator"],
        source_assurance=values["source_assurance"],
    )


def _verify_parameter_source(
    parameter: RasCalculationParameter,
    repository_root: Path,
) -> None:
    source = (repository_root / parameter.source_path).resolve()
    root = repository_root.resolve()
    if root not in source.parents:
        raise RasCalculationError("calculation source escapes repository")
    try:
        digest = sha256(source.read_bytes()).hexdigest()
    except OSError as exc:
        raise RasCalculationError("calculation source cannot be read") from exc
    if digest != parameter.source_sha256:
        raise RasCalculationError("calculation source hash mismatch")


def _validate_parameter_overlaps(
    parameters: tuple[RasCalculationParameter, ...],
) -> None:
    for index, left in enumerate(parameters):
        for right in parameters[index + 1 :]:
            if (
                left.calculation_method is right.calculation_method
                and left.parameter_name == right.parameter_name
                and left.currency == right.currency
                and left.valid_from <= (right.valid_to or date.max)
                and right.valid_from <= (left.valid_to or date.max)
            ):
                raise RasCalculationError("overlapping RAS calculation parameters")


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    missing = _required_columns() - set(fieldnames or ())
    if missing:
        raise RasCalculationError(
            f"missing calculation parameter columns: {', '.join(sorted(missing))}"
        )


def _required_columns() -> set[str]:
    return {
        "parameter_id", "version", "calculation_method", "parameter_name",
        "value", "currency", "valid_from", "valid_to", "source_path",
        "source_sha256", "source_url", "source_locator", "source_assurance",
    }
