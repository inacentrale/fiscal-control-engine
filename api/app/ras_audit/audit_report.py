import csv
import io
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from app.ras_audit.accounting_assessment import RasAccountingAssessment
from app.ras_audit.rule_resolution import RasRuleResolution
from app.ras_audit.theoretical_calculation import RasTheoreticalCalculation

RAS_REPORT_CONTRACT_VERSION = "2.0.0"
RAS_REPORT_LABELS_VERSION = "ras-report-labels-v1"


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
class RasAuditReportRecordedAmountSummary:
    certainty: RasReportCertainty
    currency: str
    case_count: int
    recorded_amount: Decimal


@dataclass(frozen=True)
class RasAuditReportVarianceSummary:
    certainty: RasReportCertainty
    currency: str
    insufficient_case_count: int
    insufficient_amount: Decimal
    excess_case_count: int
    excess_amount: Decimal


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
    period: str | None = None
    document_reference: str | None = None
    account_number: str | None = None
    operation_nature: str | None = None
    supplier_reference: str | None = None
    tax_event: str | None = None
    tax_base_amount: Decimal | None = None
    rate_percent: Decimal | None = None
    tolerance: Decimal | None = None
    rounding_policy: str | None = None
    status_label: str = "A examiner"
    review_priority: str = "normal"
    action_code: str = "review_case"
    explanation: str = "Cas a examiner."
    missing_fact_labels: tuple[str, ...] = ()
    issue_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class RasAuditExecutiveSummary:
    concluded_count: int
    probable_count: int
    indeterminate_count: int
    blocked_count: int
    error_count: int
    complete_count: int
    completeness_rate: Decimal
    top_blockers: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class RasAuditReport:
    contract_version: str
    labels_version: str
    report_id: str
    source_sha256: str
    generated_at: datetime
    case_count: int
    status_counts: tuple[tuple[str, int], ...]
    certainty_counts: tuple[tuple[str, int], ...]
    amount_summaries: tuple[RasAuditReportAmountSummary, ...]
    recorded_amount_summaries: tuple[RasAuditReportRecordedAmountSummary, ...]
    variance_summaries: tuple[RasAuditReportVarianceSummary, ...]
    details: tuple[RasAuditReportDetail, ...]
    reference_versions: tuple[str, ...]
    executive_summary: RasAuditExecutiveSummary


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
        recorded_summaries = _recorded_amount_summaries(ordered_details)
        report_id = _report_id(digest, ordered_details, normalized_versions)
        timestamp = generated_at or datetime.now(tz=UTC)
        if timestamp.tzinfo is None:
            raise ValueError("RAS report timestamp must be timezone aware")
        return RasAuditReport(
            contract_version=RAS_REPORT_CONTRACT_VERSION,
            labels_version=RAS_REPORT_LABELS_VERSION,
            report_id=report_id,
            source_sha256=digest,
            generated_at=timestamp,
            case_count=len(ordered_details),
            status_counts=status_counts,
            certainty_counts=certainty_counts,
            amount_summaries=summaries,
            recorded_amount_summaries=recorded_summaries,
            variance_summaries=_variance_summaries(ordered_details),
            details=ordered_details,
            reference_versions=normalized_versions,
            executive_summary=_executive_summary(ordered_details),
        )

    def to_json(self, report: RasAuditReport) -> str:
        return json.dumps(
            ras_report_business_payload(report),
            ensure_ascii=False,
            default=str,
            sort_keys=True,
        )

    def to_csv(self, report: RasAuditReport) -> str:
        target = io.StringIO(newline="")
        writer = csv.DictWriter(
            target,
            fieldnames=(
                "Période",
                "Pièce",
                "Compte",
                "Nature de l'opération",
                "Fournisseur",
                "Statut",
                "Priorité",
                "Action recommandée",
                "Constat",
                "Assiette fiscale",
                "Taux (%)",
                "RAS théorique",
                "RAS comptabilisée",
                "Écart comptabilisé - théorique",
                "Devise",
                "Informations manquantes",
                "Anomalies",
                "Références juridiques",
            ),
        )
        writer.writeheader()
        for detail in report.details:
            writer.writerow(
                {
                    "Période": detail.period or "",
                    "Pièce": ras_report_document_reference(detail),
                    "Compte": _spreadsheet_safe(detail.account_number or ""),
                    "Nature de l'opération": _spreadsheet_safe(
                        ras_report_operation_label(detail.operation_nature)
                    ),
                    "Fournisseur": _spreadsheet_safe(
                        detail.supplier_reference or "Non renseigné"
                    ),
                    "Statut": detail.status_label,
                    "Priorité": ras_report_priority_label(detail.review_priority),
                    "Action recommandée": ras_report_action_label(
                        detail.action_code
                    ),
                    "Constat": _spreadsheet_safe(detail.explanation),
                    "Assiette fiscale": _decimal_text(detail.tax_base_amount),
                    "Taux (%)": _decimal_text(detail.rate_percent),
                    "RAS théorique": _decimal_text(detail.expected_amount),
                    "RAS comptabilisée": _decimal_text(detail.recorded_amount),
                    "Écart comptabilisé - théorique": _decimal_text(
                        detail.difference
                    ),
                    "Devise": detail.currency or "",
                    "Informations manquantes": _spreadsheet_safe(
                        "; ".join(detail.missing_fact_labels)
                    ),
                    "Anomalies": _spreadsheet_safe("; ".join(detail.issue_labels)),
                    "Références juridiques": _spreadsheet_safe(
                        "; ".join(detail.legal_source_locators)
                    ),
                }
            )
        return target.getvalue()


def ras_report_business_payload(
    report: RasAuditReport,
    *,
    expose_document_references: bool = False,
) -> dict[str, object]:
    return {
        "generated_at": report.generated_at.isoformat(),
        "summary": {
            "case_count": report.case_count,
            "concluded_count": report.executive_summary.concluded_count,
            "probable_count": report.executive_summary.probable_count,
            "indeterminate_count": report.executive_summary.indeterminate_count,
            "blocked_count": report.executive_summary.blocked_count,
            "error_count": report.executive_summary.error_count,
            "anomaly_count": sum(
                detail.review_priority == "high" or bool(detail.issues)
                for detail in report.details
            ),
            "completeness_rate": str(report.executive_summary.completeness_rate),
            "amounts": [
                {
                    "currency": item.currency,
                    "certainty": ras_report_certainty_label(item.certainty.value),
                    "case_count": item.case_count,
                    "expected_amount": str(item.expected_amount),
                    "recorded_amount": str(item.recorded_amount),
                    "difference": str(item.difference),
                }
                for item in report.amount_summaries
            ],
            "top_blockers": [
                {"label": ras_report_fact_label(code), "count": count}
                for code, count in report.executive_summary.top_blockers
            ],
        },
        "cases": [
            ras_report_business_case(
                detail,
                expose_document_reference=expose_document_references,
            )
            for detail in report.details
        ],
        "legal_references": sorted(
            {
                locator
                for detail in report.details
                for locator in detail.legal_source_locators
            }
        ),
    }


def ras_report_business_case(
    detail: RasAuditReportDetail,
    *,
    expose_document_reference: bool = False,
) -> dict[str, object]:
    return {
        "period": detail.period,
        "document_reference": (
            detail.document_reference
            if expose_document_reference
            else ras_report_document_reference(detail)
        ),
        "account_number": detail.account_number,
        "operation_nature": ras_report_operation_label(detail.operation_nature),
        "supplier_reference": detail.supplier_reference,
        "status": detail.status_label,
        "priority": ras_report_priority_label(detail.review_priority),
        "recommended_action": ras_report_action_label(detail.action_code),
        "explanation": detail.explanation,
        "tax_base_amount": _decimal_text(detail.tax_base_amount) or None,
        "rate_percent": _decimal_text(detail.rate_percent) or None,
        "expected_amount": _decimal_text(detail.expected_amount) or None,
        "recorded_amount": _decimal_text(detail.recorded_amount) or None,
        "difference": _decimal_text(detail.difference) or None,
        "currency": detail.currency,
        "missing_information": list(detail.missing_fact_labels),
        "anomalies": list(detail.issue_labels),
        "legal_references": list(detail.legal_source_locators),
    }


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
        tax_base_amount=case.calculation.base_amount,
        rate_percent=case.calculation.rate_percent,
        tolerance=assessment.tolerance,
        rounding_policy=case.calculation.rounding_policy,
        status_label=ras_report_status_label(assessment.status.value),
        review_priority=ras_report_review_priority(assessment.status.value),
        action_code=ras_report_action_code(assessment.status.value),
        explanation=ras_report_explanation(assessment.status.value),
        missing_fact_labels=tuple(
            ras_report_fact_label(item) for item in assessment.missing_facts
        ),
        issue_labels=tuple(ras_report_issue_label(item) for item in assessment.issues),
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


def _recorded_amount_summaries(
    details: tuple[RasAuditReportDetail, ...],
) -> tuple[RasAuditReportRecordedAmountSummary, ...]:
    totals: dict[tuple[RasReportCertainty, str], list[Decimal | int]] = {}
    for detail in details:
        if detail.currency is None or detail.recorded_amount is None:
            continue
        key = (detail.certainty, detail.currency)
        values = totals.setdefault(key, [0, Decimal("0")])
        values[0] = int(values[0]) + 1
        values[1] = Decimal(values[1]) + detail.recorded_amount
    return tuple(
        RasAuditReportRecordedAmountSummary(
            certainty=certainty,
            currency=currency,
            case_count=int(values[0]),
            recorded_amount=Decimal(values[1]),
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


def _executive_summary(
    details: tuple[RasAuditReportDetail, ...],
) -> RasAuditExecutiveSummary:
    blockers = _counts(
        fact for detail in details for fact in detail.missing_facts
    )
    total = len(details)
    complete = sum(detail.basis_is_complete for detail in details)
    return RasAuditExecutiveSummary(
        concluded_count=sum(
            detail.certainty is RasReportCertainty.SUPPORTED_PROVISIONAL
            for detail in details
        ),
        probable_count=sum(
            detail.certainty is RasReportCertainty.POTENTIAL for detail in details
        ),
        indeterminate_count=sum(
            detail.certainty is RasReportCertainty.INDETERMINATE
            for detail in details
        ),
        blocked_count=sum(bool(detail.missing_facts) for detail in details),
        error_count=sum(detail.status == "failed" for detail in details),
        complete_count=complete,
        completeness_rate=(
            Decimal(complete) / Decimal(total) if total else Decimal("0")
        ),
        top_blockers=tuple(
            sorted(blockers, key=lambda item: (-item[1], item[0]))[:5]
        ),
    )


def _variance_summaries(
    details: tuple[RasAuditReportDetail, ...],
) -> tuple[RasAuditReportVarianceSummary, ...]:
    totals: dict[tuple[RasReportCertainty, str], list[Decimal | int]] = {}
    for detail in details:
        if detail.currency is None or detail.difference is None:
            continue
        key = (detail.certainty, detail.currency)
        values = totals.setdefault(
            key,
            [0, Decimal("0"), 0, Decimal("0")],
        )
        if detail.difference < 0:
            values[0] = int(values[0]) + 1
            values[1] = Decimal(values[1]) + abs(detail.difference)
        elif detail.difference > 0:
            values[2] = int(values[2]) + 1
            values[3] = Decimal(values[3]) + detail.difference
    return tuple(
        RasAuditReportVarianceSummary(
            certainty=certainty,
            currency=currency,
            insufficient_case_count=int(values[0]),
            insufficient_amount=Decimal(values[1]),
            excess_case_count=int(values[2]),
            excess_amount=Decimal(values[3]),
        )
        for (certainty, currency), values in sorted(
            totals.items(),
            key=lambda item: (item[0][0].value, item[0][1]),
        )
    )


def ras_report_status_label(status: str) -> str:
    return {
        "provisional_reconciled": "RAS rapprochée provisoirement",
        "provisional_amount_mismatch": "Écart de montant à régulariser",
        "provisional_ras_not_found_in_gl": "RAS non retrouvée dans le Grand Livre",
        "potential_related_entry": "Contrepartie probable a confirmer",
        "currency_mismatch": "Devise incohérente",
        "indeterminate": "Analyse indéterminable",
        "applicability_probable_to_confirm": "Applicabilité probable à confirmer",
        "indeterminate_missing_data": "Données manquantes",
    }.get(status, "Cas à examiner")


def ras_report_review_priority(status: str) -> str:
    if status in {"provisional_ras_not_found_in_gl", "provisional_amount_mismatch"}:
        return "high"
    if status in {"currency_mismatch", "indeterminate", "indeterminate_missing_data"}:
        return "medium"
    if status == "applicability_probable_to_confirm":
        return "medium"
    return "normal"


def ras_report_action_code(status: str) -> str:
    return {
        "provisional_reconciled": "document_review",
        "provisional_amount_mismatch": "review_amount_difference",
        "provisional_ras_not_found_in_gl": "review_missing_ras_entry",
        "potential_related_entry": "confirm_document_link",
        "currency_mismatch": "confirm_currency",
        "indeterminate": "provide_missing_facts",
        "indeterminate_missing_data": "provide_missing_facts",
        "applicability_probable_to_confirm": "confirm_applicability_facts",
    }.get(status, "review_case")


def ras_report_certainty_label(certainty: str) -> str:
    return {
        "supported_provisional": "Conclusion provisoire étayée",
        "potential": "Cas probable à confirmer",
        "indeterminate": "Analyse indéterminable",
    }.get(certainty, "Niveau à confirmer")


def ras_report_priority_label(priority: str) -> str:
    return {
        "high": "Haute",
        "medium": "Moyenne",
        "normal": "Normale",
    }.get(priority, "À définir")


def ras_report_action_label(action_code: str) -> str:
    return {
        "document_review": "Contrôler la pièce justificative",
        "review_amount_difference": "Vérifier et régulariser l'écart",
        "review_missing_ras_entry": "Rechercher ou comptabiliser la RAS",
        "confirm_document_link": "Confirmer le lien entre les pièces",
        "confirm_currency": "Confirmer la devise de rapprochement",
        "provide_missing_facts": "Compléter les informations manquantes",
        "confirm_applicability_facts": "Confirmer les conditions fiscales",
        "review_case": "Effectuer une revue du dossier",
    }.get(action_code, "Effectuer une revue du dossier")


def ras_report_operation_label(operation_nature: str | None) -> str:
    if not operation_nature:
        return "Nature à déterminer"
    return {
        "professional_service": "Honoraires ou prestation professionnelle",
        "temporary_staffing_service": "Prestation de travail temporaire",
        "real_estate_work": "Travaux immobiliers ou travaux publics",
        "rent": "Loyer",
        "service": "Prestation de services",
        "assistance_service": "Prestation d'assistance",
        "study_service": "Étude ou conseil",
        "rental": "Location",
        "royalty": "Redevance",
        "internal_treasury_transfer": "Transfert interne de trésorerie",
        "reversal": "Extourne ou annulation comptable",
        "service_any": "Prestation de services",
        "construction_work": "Travaux de construction",
        "temporary_staffing": "Travail temporaire",
        "real_estate_rental": "Location immobilière",
        "manual_or_teaching": "Prestation manuelle ou enseignement",
        "public_parapublic": "Entité publique ou parapublique",
        "occasional_intellectual": "Prestation intellectuelle occasionnelle",
        "other_legal_entity": "Autre personne morale",
        "public_parapublic_or_nonprofit": (
            "Entité publique, parapublique ou sans but lucratif"
        ),
        "public_authorized_service_receipt_exempt": (
            "Recette de service public autorisée susceptible d'exonération"
        ),
    }.get(operation_nature, operation_nature.replace("_", " ").capitalize())


def ras_report_document_reference(detail: RasAuditReportDetail) -> str:
    digest = sha256(detail.candidate_id.encode()).hexdigest()[:12].upper()
    return f"PIECE-{digest}"


def ras_report_explanation(status: str) -> str:
    return {
        "provisional_reconciled": (
            "Le montant comptabilise est dans la tolerance sourcee."
        ),
        "provisional_amount_mismatch": (
            "Le montant comptabilise differe du montant theorique "
            "au-dela de la tolerance."
        ),
        "provisional_ras_not_found_in_gl": (
            "Aucune RAS n'a ete retrouvee dans le perimetre comptable complet."
        ),
        "potential_related_entry": "Une contrepartie possible doit etre confirmee.",
        "currency_mismatch": "Les devises ne permettent pas un rapprochement fiable.",
        "indeterminate": "Des faits requis manquent pour conclure.",
        "indeterminate_missing_data": "Des faits requis manquent pour conclure.",
        "applicability_probable_to_confirm": (
            "Des signaux comptables existent; les faits fiscaux doivent etre confirmes."
        ),
    }.get(status, "Le cas necessite une revue humaine.")


def ras_report_fact_label(code: str) -> str:
    return {
        "legal_facts_per_candidate": "Faits juridiques propres au cas",
        "residence_status": "Statut de residence du beneficiaire",
        "ifu_status": "Statut IFU du beneficiaire",
        "operation_type": "Nature fiscale de l'operation",
        "exemption_status": "Situation d'exoneration",
        "payment_status": "Statut du paiement",
        "payment_date": "Date du fait generateur",
        "tax_base_amount": "Assiette fiscale",
        "currency": "Devise",
        "same_currency_counterpart": "Contrepartie dans la meme devise",
        "confirmed_document_link": "Lien confirme avec la piece",
        "recorded_ras_amount": "Montant de RAS comptabilise",
        "accounting_tolerance_policy": "Politique de tolerance comptable",
        "candidate_requires_category_split": "Ventilation par categorie fiscale",
        "posting_key_side": "Sens de l'ecriture comptable",
        "strong_semantic_signal": "Signal sémantique fort à confirmer",
        "semantic_disambiguation": "Nature de l'opération à préciser",
        "company_code": "Périmètre de société",
        "partner_id": "Tiers concerné",
        "source_scope_completeness": "Complétude du Grand Livre",
        "applicable_ras_account_mapping": "Compte de contrepartie RAS applicable",
    }.get(code, code.replace("_", " ").capitalize())


def ras_report_issue_label(code: str) -> str:
    labels = {
        "partial_ras_recorded": "RAS partiellement comptabilisee",
        "ras_recorded_above_expected": "RAS comptabilisee superieure au theorique",
        "net_ras_reversal_exceeds_recording": "Reprise nette superieure a la RAS",
        "document_link_not_confirmed": "Lien avec la piece non confirme",
        "counterpart:found_in_same_entry": "Contrepartie RAS retrouvée dans la pièce",
        "counterpart:potential_related_entry": "Contrepartie possible à confirmer",
        "counterpart:not_found_in_scope": (
            "Contrepartie non retrouvée dans le périmètre"
        ),
        "counterpart:indeterminate": "Recherche de contrepartie indéterminable",
        "counterpart:not_evaluated_for_candidate": (
            "Recherche de contrepartie non réalisable pour ce dossier"
        ),
    }
    return labels.get(code, "Anomalie comptable à examiner")


def _report_id(
    source_sha256: str,
    details: tuple[RasAuditReportDetail, ...],
    versions: tuple[str, ...],
) -> str:
    material = {
        "contract_version": RAS_REPORT_CONTRACT_VERSION,
        "labels_version": RAS_REPORT_LABELS_VERSION,
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
                "period": detail.period,
                "document_reference": detail.document_reference,
                "account_number": detail.account_number,
                "operation_nature": detail.operation_nature,
                "supplier_reference": detail.supplier_reference,
                "tax_event": detail.tax_event,
                "tax_base_amount": _decimal_text(detail.tax_base_amount),
                "rate_percent": _decimal_text(detail.rate_percent),
                "tolerance": _decimal_text(detail.tolerance),
                "rounding_policy": detail.rounding_policy,
                "review_priority": detail.review_priority,
                "action_code": detail.action_code,
                "status_label": detail.status_label,
                "explanation": detail.explanation,
                "missing_fact_labels": detail.missing_fact_labels,
                "issue_labels": detail.issue_labels,
            }
            for detail in details
        ],
    }
    serialized = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def _decimal_text(value: Decimal | None) -> str:
    return str(value) if value is not None else ""


def _spreadsheet_safe(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value
