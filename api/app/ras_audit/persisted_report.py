from decimal import Decimal, InvalidOperation

from app.ras_audit.audit_report import (
    RasAuditReport,
    RasAuditReportDetail,
    RasAuditReportGenerator,
    RasReportCertainty,
    ras_report_action_code,
    ras_report_explanation,
    ras_report_fact_label,
    ras_report_issue_label,
    ras_report_review_priority,
    ras_report_status_label,
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
    status = _text(payload, "status")
    missing_facts = _text_tuple(payload, "missing_facts")
    issues = _text_tuple(payload, "issues")
    return RasAuditReportDetail(
        candidate_id=_text(payload, "candidate_id"),
        status=status,
        certainty=RasReportCertainty(_text(payload, "certainty")),
        rule_id=_optional_text(payload, "rule_id"),
        rule_version=_optional_text(payload, "rule_version"),
        expected_amount=_optional_decimal(payload, "expected_amount"),
        recorded_amount=_optional_decimal(payload, "recorded_amount"),
        difference=_optional_decimal(payload, "difference"),
        currency=_optional_text(payload, "currency"),
        missing_facts=missing_facts,
        issues=issues,
        legal_source_locators=_text_tuple(payload, "legal_source_locators"),
        basis_is_complete=_boolean(payload, "basis_is_complete"),
        period=_optional_payload_text(payload, "period"),
        document_reference=_optional_payload_text(payload, "document_reference"),
        account_number=_optional_payload_text(payload, "account_number"),
        operation_nature=_optional_payload_text(payload, "operation_nature"),
        supplier_reference=_optional_payload_text(payload, "supplier_reference"),
        tax_event=_optional_payload_text(payload, "tax_event"),
        tax_base_amount=_optional_payload_decimal(payload, "tax_base_amount"),
        rate_percent=_optional_payload_decimal(payload, "rate_percent"),
        tolerance=_optional_payload_decimal(payload, "tolerance"),
        rounding_policy=_optional_payload_text(payload, "rounding_policy"),
        status_label=(
            _optional_payload_text(payload, "status_label")
            or ras_report_status_label(status)
        ),
        review_priority=(
            _optional_payload_text(payload, "review_priority")
            or ras_report_review_priority(status)
        ),
        action_code=(
            _optional_payload_text(payload, "action_code")
            or ras_report_action_code(status)
        ),
        explanation=(
            _optional_payload_text(payload, "explanation")
            or ras_report_explanation(status)
        ),
        missing_fact_labels=(
            _optional_text_tuple(payload, "missing_fact_labels")
            or tuple(ras_report_fact_label(item) for item in missing_facts)
        ),
        issue_labels=(
            _optional_text_tuple(payload, "issue_labels")
            or tuple(ras_report_issue_label(item) for item in issues)
        ),
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


def _optional_payload_text(payload: dict[str, object], name: str) -> str | None:
    if name not in payload or payload[name] is None:
        return None
    return _optional_text(payload, name)


def _optional_payload_decimal(
    payload: dict[str, object], name: str
) -> Decimal | None:
    if name not in payload or payload[name] is None:
        return None
    return _optional_decimal(payload, name)


def _optional_text_tuple(
    payload: dict[str, object], name: str
) -> tuple[str, ...]:
    if name not in payload:
        return ()
    return _text_tuple(payload, name)
