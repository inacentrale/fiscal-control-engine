from decimal import Decimal, InvalidOperation

from app.ras_audit.audit_report import (
    RasAuditReport,
    RasAuditReportDetail,
    RasAuditReportGenerator,
    RasReportCertainty,
)
from app.ras_audit.persistence import SqlAlchemyRasAuditRepository


class PersistedRasAuditReportError(ValueError):
    pass


class PersistedRasAuditReportService:
    def __init__(self, repository: SqlAlchemyRasAuditRepository) -> None:
        self._repository = repository

    def generate(self, audit_id: str) -> RasAuditReport:
        snapshot = self._repository.get(audit_id.strip())
        if snapshot is None:
            raise PersistedRasAuditReportError("RAS audit was not found")
        try:
            details = tuple(_detail(case.payload) for case in snapshot.cases)
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise PersistedRasAuditReportError(
                "persisted RAS audit case is invalid"
            ) from exc
        if tuple(detail.candidate_id for detail in details) != tuple(
            case.candidate_id for case in snapshot.cases
        ):
            raise PersistedRasAuditReportError(
                "persisted RAS candidate identity mismatch"
            )
        report = RasAuditReportGenerator().generate_from_details(
            source_sha256=snapshot.source_sha256,
            details=details,
            reference_versions=snapshot.reference_versions,
            generated_at=snapshot.created_at,
        )
        self._repository.append_event(
            snapshot.audit_id,
            event_type="report_generated",
            metadata={"report_id": report.report_id, "case_count": report.case_count},
        )
        return report


def _detail(payload: dict[str, object]) -> RasAuditReportDetail:
    return RasAuditReportDetail(
        candidate_id=_text(payload, "candidate_id"),
        status=_text(payload, "status"),
        certainty=RasReportCertainty(_text(payload, "certainty")),
        rule_id=_optional_text(payload, "rule_id"),
        rule_version=_optional_text(payload, "rule_version"),
        expected_amount=_optional_decimal(payload, "expected_amount"),
        recorded_amount=_optional_decimal(payload, "recorded_amount"),
        difference=_optional_decimal(payload, "difference"),
        currency=_optional_text(payload, "currency"),
        missing_facts=_text_tuple(payload, "missing_facts"),
        issues=_text_tuple(payload, "issues"),
        legal_source_locators=_text_tuple(payload, "legal_source_locators"),
        basis_is_complete=_boolean(payload, "basis_is_complete"),
    )


def _text(payload: dict[str, object], name: str) -> str:
    value = payload[name]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid persisted RAS field: {name}")
    return value.strip()


def _optional_text(payload: dict[str, object], name: str) -> str | None:
    value = payload[name]
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid persisted RAS field: {name}")
    return value.strip()


def _optional_decimal(payload: dict[str, object], name: str) -> Decimal | None:
    value = payload[name]
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid persisted RAS field: {name}")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError(f"invalid persisted RAS field: {name}")
    return result


def _text_tuple(payload: dict[str, object], name: str) -> tuple[str, ...]:
    value = payload[name]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"invalid persisted RAS field: {name}")
    return tuple(value)


def _boolean(payload: dict[str, object], name: str) -> bool:
    value = payload[name]
    if not isinstance(value, bool):
        raise ValueError(f"invalid persisted RAS field: {name}")
    return value
