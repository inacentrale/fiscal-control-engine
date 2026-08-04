from dataclasses import dataclass
from enum import StrEnum

from app.ras_audit.domain import AuditCapability, LedgerField


class CapabilityReadinessStatus(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class LedgerReadinessInput:
    available_fields: frozenset[LedgerField]
    source_scope_complete: bool | None = None
    ras_account_mapping_available: bool = False
    posting_keys_complete: bool = False


@dataclass(frozen=True)
class CapabilityReadiness:
    capability: AuditCapability
    status: CapabilityReadinessStatus
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LedgerReadinessReport:
    capabilities: tuple[CapabilityReadiness, ...]

    def for_capability(self, capability: AuditCapability) -> CapabilityReadiness:
        for readiness in self.capabilities:
            if readiness.capability is capability:
                return readiness
        raise KeyError(f"capability readiness is unavailable: {capability}")


def assess_ledger_readiness(profile: LedgerReadinessInput) -> LedgerReadinessReport:
    return LedgerReadinessReport(
        capabilities=(
            _candidate_detection_readiness(profile),
            _legal_rule_readiness(profile),
            _theoretical_calculation_readiness(profile),
            _counterpart_reconciliation_readiness(profile),
        ),
    )


def _candidate_detection_readiness(
    profile: LedgerReadinessInput,
) -> CapabilityReadiness:
    blockers: list[str] = []
    if not (
        LedgerField.ACCOUNT_NUMBER in profile.available_fields
        or LedgerField.LABEL in profile.available_fields
    ):
        blockers.append("missing_account_and_label")
    warnings: list[str] = []
    if (
        LedgerField.POSTING_KEY in profile.available_fields
        and not profile.posting_keys_complete
    ):
        warnings.append("posting_keys_incomplete")
    return _readiness(
        AuditCapability.CANDIDATE_DETECTION,
        blockers=blockers,
        warnings=warnings,
    )


def _legal_rule_readiness(profile: LedgerReadinessInput) -> CapabilityReadiness:
    blockers = _missing_field_blockers(
        profile,
        (LedgerField.POSTING_DATE,),
    )
    return _readiness(AuditCapability.LEGAL_RULE_RESOLUTION, blockers=blockers)


def _theoretical_calculation_readiness(
    profile: LedgerReadinessInput,
) -> CapabilityReadiness:
    blockers = _missing_field_blockers(
        profile,
        (
            LedgerField.AMOUNT,
            LedgerField.CURRENCY,
            LedgerField.POSTING_DATE,
        ),
    )
    return _readiness(AuditCapability.THEORETICAL_CALCULATION, blockers=blockers)


def _counterpart_reconciliation_readiness(
    profile: LedgerReadinessInput,
) -> CapabilityReadiness:
    blockers = _missing_field_blockers(
        profile,
        (
            LedgerField.COMPANY_CODE,
            LedgerField.FISCAL_YEAR,
            LedgerField.JOURNAL,
            LedgerField.DOCUMENT_NUMBER,
            LedgerField.ACCOUNT_NUMBER,
            LedgerField.POSTING_KEY,
            LedgerField.AMOUNT,
            LedgerField.CURRENCY,
        ),
    )
    if not profile.posting_keys_complete:
        blockers.append("posting_keys_incomplete")
    if not profile.ras_account_mapping_available:
        blockers.append("ras_account_mapping_unavailable")
    if profile.source_scope_complete is not True:
        blockers.append("source_scope_not_confirmed_complete")
    return _readiness(
        AuditCapability.COUNTERPART_RECONCILIATION,
        blockers=blockers,
    )


def _missing_field_blockers(
    profile: LedgerReadinessInput,
    required_fields: tuple[LedgerField, ...],
) -> list[str]:
    return [
        f"missing_{field.value}"
        for field in required_fields
        if field not in profile.available_fields
    ]


def _readiness(
    capability: AuditCapability,
    *,
    blockers: list[str],
    warnings: list[str] | None = None,
) -> CapabilityReadiness:
    normalized_warnings = tuple(warnings or ())
    if blockers:
        status = CapabilityReadinessStatus.BLOCKED
    elif normalized_warnings:
        status = CapabilityReadinessStatus.DEGRADED
    else:
        status = CapabilityReadinessStatus.READY
    return CapabilityReadiness(
        capability=capability,
        status=status,
        blockers=tuple(blockers),
        warnings=normalized_warnings,
    )
