import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path

from app.ras_audit.domain import CanonicalLedgerEntry, LedgerSourceReference


class GoldenDatasetError(ValueError):
    pass


class GoldenExpectedCounterpart(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    NOT_APPLICABLE = "not_applicable"
    INDETERMINATE = "indeterminate"


class GoldenLedgerRole(StrEnum):
    EXPENSE = "expense"
    PAYABLE = "payable"
    RAS_COUNTERPART = "ras_counterpart"
    TREASURY = "treasury"
    REVERSAL = "reversal"
    ADJUSTMENT = "adjustment"


class QualityGateDirection(StrEnum):
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


@dataclass(frozen=True)
class GoldenLedgerLine:
    entry: CanonicalLedgerEntry
    role: GoldenLedgerRole

    @property
    def partner_id(self) -> str | None:
        return self.entry.partner_id


@dataclass(frozen=True)
class GoldenScenario:
    scenario_id: str
    description: str
    coverage_tags: frozenset[str]
    expected_candidate_signal: bool
    expected_counterpart: GoldenExpectedCounterpart
    legal_rule_id: str | None
    lines: tuple[GoldenLedgerLine, ...]

    @property
    def entries(self) -> tuple[CanonicalLedgerEntry, ...]:
        return tuple(line.entry for line in self.lines)


@dataclass(frozen=True)
class GoldenDataset:
    scenarios: tuple[GoldenScenario, ...]

    @property
    def coverage_tags(self) -> frozenset[str]:
        return frozenset(
            tag for scenario in self.scenarios for tag in scenario.coverage_tags
        )


@dataclass(frozen=True)
class QualityGate:
    metric_name: str
    direction: QualityGateDirection
    threshold: Decimal
    unit: str
    description: str


def load_golden_dataset(directory: Path) -> GoldenDataset:
    ledger_rows = _read_csv(directory / "ledger.csv")
    expectation_rows = _read_csv(directory / "expectations.csv")
    lines_by_scenario = _load_ledger_lines(ledger_rows)

    scenarios: list[GoldenScenario] = []
    seen_scenarios: set[str] = set()
    for row_number, row in enumerate(expectation_rows, start=2):
        scenario_id = _synthetic_id(row, "scenario_id", row_number)
        if scenario_id in seen_scenarios:
            raise GoldenDatasetError(f"duplicate scenario id at row {row_number}")
        seen_scenarios.add(scenario_id)
        lines = lines_by_scenario.get(scenario_id)
        if not lines:
            raise GoldenDatasetError(
                f"scenario {scenario_id} has no ledger entries"
            )
        scenarios.append(
            GoldenScenario(
                scenario_id=scenario_id,
                description=_required(row, "description", row_number),
                coverage_tags=_coverage_tags(row, row_number),
                expected_candidate_signal=_boolean(
                    row,
                    "expected_candidate_signal",
                    row_number,
                ),
                expected_counterpart=_enum_value(
                    GoldenExpectedCounterpart,
                    row,
                    "expected_counterpart",
                    row_number,
                ),
                legal_rule_id=_optional(row.get("legal_rule_id")),
                lines=lines,
            ),
        )

    orphan_ledger_scenarios = sorted(set(lines_by_scenario) - seen_scenarios)
    if orphan_ledger_scenarios:
        raise GoldenDatasetError(
            "ledger scenarios have no expectation: "
            + ", ".join(orphan_ledger_scenarios)
        )
    return GoldenDataset(scenarios=tuple(scenarios))


def load_quality_gates(path: Path) -> tuple[QualityGate, ...]:
    rows = _read_csv(path)
    gates: list[QualityGate] = []
    seen_metrics: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        metric_name = _required(row, "metric_name", row_number)
        if metric_name in seen_metrics:
            raise GoldenDatasetError(f"duplicate quality metric at row {row_number}")
        seen_metrics.add(metric_name)
        threshold = _decimal(row, "threshold", row_number)
        unit = _required(row, "unit", row_number)
        if unit == "ratio" and not Decimal("0") <= threshold <= Decimal("1"):
            raise GoldenDatasetError(
                f"ratio threshold must be between 0 and 1 at row {row_number}"
            )
        gates.append(
            QualityGate(
                metric_name=metric_name,
                direction=_enum_value(
                    QualityGateDirection,
                    row,
                    "direction",
                    row_number,
                ),
                threshold=threshold,
                unit=unit,
                description=_required(row, "description", row_number),
            ),
        )
    return tuple(gates)


def _load_ledger_lines(
    rows: tuple[dict[str, str], ...],
) -> dict[str, tuple[GoldenLedgerLine, ...]]:
    mutable_lines: dict[str, list[GoldenLedgerLine]] = {}
    seen_line_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        scenario_id = _synthetic_id(row, "scenario_id", row_number)
        line_id = _synthetic_id(row, "line_id", row_number)
        if line_id in seen_line_ids:
            raise GoldenDatasetError(f"duplicate ledger line id at row {row_number}")
        seen_line_ids.add(line_id)
        partner_id = _optional(row.get("partner_id"))
        if partner_id is not None and not partner_id.startswith("SYN-TIERS-"):
            raise GoldenDatasetError(
                f"partner id must be synthetic at row {row_number}"
            )
        entry = CanonicalLedgerEntry(
            line_id=line_id,
            source=LedgerSourceReference(
                file_name="synthetic-ras-audit-golden-ledger.csv",
                content_sha256="0" * 64,
                sheet_name="ledger",
                row_number=row_number,
            ),
            company_code=_optional(row.get("company_code")),
            fiscal_year=_integer(row, "fiscal_year", row_number),
            period=_integer(row, "period", row_number),
            journal=_optional(row.get("journal")),
            document_number=_optional(row.get("document_number")),
            line_number=_optional(row.get("line_number")),
            posting_date=_date(row, "posting_date", row_number),
            account_number=_optional(row.get("account_number")),
            partner_id=partner_id,
            label=_optional(row.get("label")),
            posting_key=_optional(row.get("posting_key")),
            amount=_decimal(row, "amount", row_number),
            currency=_optional(row.get("currency")),
        )
        mutable_lines.setdefault(scenario_id, []).append(
            GoldenLedgerLine(
                entry=entry,
                role=_enum_value(
                    GoldenLedgerRole,
                    row,
                    "role",
                    row_number,
                ),
            ),
        )
    return {
        scenario_id: tuple(lines)
        for scenario_id, lines in mutable_lines.items()
    }


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            return tuple(csv.DictReader(source))
    except OSError as exc:
        raise GoldenDatasetError(f"golden dataset cannot be read: {path.name}") from exc


def _required(row: dict[str, str], field: str, row_number: int) -> str:
    value = _optional(row.get(field))
    if value is None:
        raise GoldenDatasetError(f"{field} is required at row {row_number}")
    return value


def _synthetic_id(row: dict[str, str], field: str, row_number: int) -> str:
    value = _required(row, field, row_number)
    if not value.startswith("SYN-"):
        raise GoldenDatasetError(f"{field} must be synthetic at row {row_number}")
    return value


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _integer(row: dict[str, str], field: str, row_number: int) -> int:
    value = _required(row, field, row_number)
    try:
        return int(value)
    except ValueError as exc:
        raise GoldenDatasetError(f"invalid {field} at row {row_number}") from exc


def _decimal(row: dict[str, str], field: str, row_number: int) -> Decimal:
    value = _required(row, field, row_number)
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise GoldenDatasetError(f"invalid {field} at row {row_number}") from exc
    if not result.is_finite():
        raise GoldenDatasetError(f"invalid {field} at row {row_number}")
    return result


def _date(row: dict[str, str], field: str, row_number: int) -> date:
    value = _required(row, field, row_number)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise GoldenDatasetError(f"invalid {field} at row {row_number}") from exc


def _boolean(row: dict[str, str], field: str, row_number: int) -> bool:
    value = _required(row, field, row_number).lower()
    if value not in {"true", "false"}:
        raise GoldenDatasetError(f"invalid {field} at row {row_number}")
    return value == "true"


def _coverage_tags(row: dict[str, str], row_number: int) -> frozenset[str]:
    tags = frozenset(
        tag.strip()
        for tag in _required(row, "coverage_tags", row_number).split(";")
        if tag.strip()
    )
    if not tags:
        raise GoldenDatasetError(f"coverage_tags is required at row {row_number}")
    return tags


def _enum_value[T: StrEnum](
    enum_type: type[T],
    row: dict[str, str],
    field: str,
    row_number: int,
) -> T:
    value = _required(row, field, row_number)
    try:
        return enum_type(value)
    except ValueError as exc:
        raise GoldenDatasetError(f"invalid {field} at row {row_number}") from exc
