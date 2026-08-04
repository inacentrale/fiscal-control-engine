import csv
import io
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from app.ras_audit.accounting_assessment import RasAccountingAssessment
from app.ras_audit.rule_resolution import RasRuleResolution
from app.ras_audit.theoretical_calculation import RasTheoreticalCalculation


class RasReportCertainty(StrEnum):
    SUPPORTED_PROVISIONAL = "supported_provisional"
    POTENTIAL = "potential"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class RasAuditReportCase:
    candidate_id: str
    assessment: RasAccountingAssessment
    resolution: RasRuleResolution
    calculation: RasTheoreticalCalculation

    def __post_init__(self) -> None:
        candidate_id = self.candidate_id.strip()
        if not candidate_id:
            raise ValueError("RAS report candidate id is required")
        if candidate_id != self.assessment.candidate_entry_id:
            raise ValueError("RAS report candidate identifiers do not match")
        object.__setattr__(self, "candidate_id", candidate_id)


@dataclass(frozen=True)
class RasAuditReportAmountSummary:
    certainty: RasReportCertainty
    currency: str
    case_count: int
    expected_amount: Decimal
    recorded_amount: Decimal
    difference: Decimal


@dataclass(frozen=True)
class RasAuditReportDetail:
    candidate_id: str
    status: str
    certainty: RasReportCertainty
    rule_id: str | None
    rule_version: str | None
    expected_amount: Decimal | None
    recorded_amount: Decimal | None
    difference: Decimal | None
    currency: str | None
    missing_facts: tuple[str, ...]
    issues: tuple[str, ...]
    legal_source_locators: tuple[str, ...]
    basis_is_complete: bool


@dataclass(frozen=True)
class RasAuditReport:
    report_id: str
    source_sha256: str
    generated_at: datetime
    case_count: int
    status_counts: tuple[tuple[str, int], ...]
    certainty_counts: tuple[tuple[str, int], ...]
    amount_summaries: tuple[RasAuditReportAmountSummary, ...]
    details: tuple[RasAuditReportDetail, ...]
    reference_versions: tuple[str, ...]


class RasAuditReportGenerator:
    def generate(
        self,
        *,
        source_sha256: str,
        cases: tuple[RasAuditReportCase, ...],
        reference_versions: tuple[str, ...],
        generated_at: datetime | None = None,
    ) -> RasAuditReport:
        digest = source_sha256.strip().lower()
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise ValueError("RAS report source hash is invalid")
        if len({case.candidate_id for case in cases}) != len(cases):
            raise ValueError("duplicate RAS report candidate")
        normalized_versions = tuple(sorted(set(reference_versions)))
        if not normalized_versions or any(
            not version.strip() for version in normalized_versions
        ):
            raise ValueError("RAS report reference versions are required")
        details = tuple(
            _detail(case) for case in sorted(cases, key=lambda item: item.candidate_id)
        )
        return self.generate_from_details(
            source_sha256=digest,
            details=details,
            reference_versions=normalized_versions,
            generated_at=generated_at,
        )

    def generate_from_details(
        self,
        *,
        source_sha256: str,
        details: tuple[RasAuditReportDetail, ...],
        reference_versions: tuple[str, ...],
        generated_at: datetime | None = None,
    ) -> RasAuditReport:
        digest = source_sha256.strip().lower()
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise ValueError("RAS report source hash is invalid")
        if len({detail.candidate_id for detail in details}) != len(details):
            raise ValueError("duplicate RAS report candidate")
        normalized_versions = tuple(sorted(set(reference_versions)))
        if not normalized_versions or any(
            not version.strip() for version in normalized_versions
        ):
            raise ValueError("RAS report reference versions are required")
        ordered_details = tuple(sorted(details, key=lambda item: item.candidate_id))
        status_counts = _counts(detail.status for detail in ordered_details)
        certainty_counts = _counts(detail.certainty.value for detail in details)
        summaries = _amount_summaries(ordered_details)
        report_id = _report_id(digest, ordered_details, normalized_versions)
        timestamp = generated_at or datetime.now(tz=UTC)
        if timestamp.tzinfo is None:
            raise ValueError("RAS report timestamp must be timezone aware")
        return RasAuditReport(
            report_id=report_id,
            source_sha256=digest,
            generated_at=timestamp,
            case_count=len(ordered_details),
            status_counts=status_counts,
            certainty_counts=certainty_counts,
            amount_summaries=summaries,
            details=ordered_details,
            reference_versions=normalized_versions,
        )

    def to_json(self, report: RasAuditReport) -> str:
        payload = asdict(report)
        payload["generated_at"] = report.generated_at.isoformat()
        return json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)

    def to_csv(self, report: RasAuditReport) -> str:
        target = io.StringIO(newline="")
        writer = csv.DictWriter(
            target,
            fieldnames=(
                "candidate_id",
                "status",
                "certainty",
                "rule_id",
                "rule_version",
                "expected_amount",
                "recorded_amount",
                "difference",
                "currency",
                "missing_facts",
                "issues",
                "legal_source_locators",
                "basis_is_complete",
            ),
        )
        writer.writeheader()
        for detail in report.details:
            writer.writerow(
                {
                    "candidate_id": detail.candidate_id,
                    "status": detail.status,
                    "certainty": detail.certainty.value,
                    "rule_id": detail.rule_id or "",
                    "rule_version": detail.rule_version or "",
                    "expected_amount": _decimal_text(detail.expected_amount),
                    "recorded_amount": _decimal_text(detail.recorded_amount),
                    "difference": _decimal_text(detail.difference),
                    "currency": detail.currency or "",
                    "missing_facts": ";".join(detail.missing_facts),
                    "issues": ";".join(detail.issues),
                    "legal_source_locators": ";".join(detail.legal_source_locators),
                    "basis_is_complete": str(detail.basis_is_complete).lower(),
                }
            )
        return target.getvalue()


def _detail(case: RasAuditReportCase) -> RasAuditReportDetail:
    assessment = case.assessment
    return RasAuditReportDetail(
        candidate_id=case.candidate_id,
        status=assessment.status.value,
        certainty=_certainty(assessment),
        rule_id=case.resolution.rule_id,
        rule_version=case.resolution.rule_version,
        expected_amount=assessment.expected_amount,
        recorded_amount=assessment.recorded_amount,
        difference=assessment.difference,
        currency=assessment.currency,
        missing_facts=assessment.missing_facts,
        issues=assessment.issues,
        legal_source_locators=tuple(
            evidence.source_locator for evidence in case.resolution.evidence
        ),
        basis_is_complete=assessment.basis_is_complete,
    )


def _certainty(assessment: RasAccountingAssessment) -> RasReportCertainty:
    if assessment.basis_is_complete:
        return RasReportCertainty.SUPPORTED_PROVISIONAL
    if assessment.status.value == "potential_related_entry":
        return RasReportCertainty.POTENTIAL
    return RasReportCertainty.INDETERMINATE


def _amount_summaries(
    details: tuple[RasAuditReportDetail, ...],
) -> tuple[RasAuditReportAmountSummary, ...]:
    totals: dict[tuple[RasReportCertainty, str], list[Decimal | int]] = {}
    for detail in details:
        if (
            detail.currency is None
            or detail.expected_amount is None
            or detail.recorded_amount is None
            or detail.difference is None
        ):
            continue
        key = (detail.certainty, detail.currency)
        values = totals.setdefault(
            key,
            [0, Decimal("0"), Decimal("0"), Decimal("0")],
        )
        values[0] = int(values[0]) + 1
        values[1] = Decimal(values[1]) + detail.expected_amount
        values[2] = Decimal(values[2]) + detail.recorded_amount
        values[3] = Decimal(values[3]) + detail.difference
    return tuple(
        RasAuditReportAmountSummary(
            certainty=certainty,
            currency=currency,
            case_count=int(values[0]),
            expected_amount=Decimal(values[1]),
            recorded_amount=Decimal(values[2]),
            difference=Decimal(values[3]),
        )
        for (certainty, currency), values in sorted(
            totals.items(),
            key=lambda item: (item[0][0].value, item[0][1]),
        )
    )


def _counts(values: Iterable[str]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return tuple(sorted(counts.items()))


def _report_id(
    source_sha256: str,
    details: tuple[RasAuditReportDetail, ...],
    versions: tuple[str, ...],
) -> str:
    material = {
        "source_sha256": source_sha256,
        "reference_versions": versions,
        "details": [
            {
                "candidate_id": detail.candidate_id,
                "status": detail.status,
                "certainty": detail.certainty.value,
                "rule_id": detail.rule_id,
                "rule_version": detail.rule_version,
                "expected": _decimal_text(detail.expected_amount),
                "recorded": _decimal_text(detail.recorded_amount),
                "difference": _decimal_text(detail.difference),
                "currency": detail.currency,
                "missing_facts": detail.missing_facts,
                "issues": detail.issues,
                "legal_source_locators": detail.legal_source_locators,
                "basis_is_complete": detail.basis_is_complete,
            }
            for detail in details
        ],
    }
    serialized = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def _decimal_text(value: Decimal | None) -> str:
    return str(value) if value is not None else ""
