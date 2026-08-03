from dataclasses import dataclass

from app.tax_declaration.assurance_policy import TaxAssurancePolicy
from app.tax_declaration.validation_domain import (
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationStatus,
)


@dataclass(frozen=True)
class TaxAssuranceAssessment:
    level: str
    policy_id: str | None
    policy_version: str | None
    description: str
    passed_layers: tuple[ValidationLayer, ...]
    missing_layers: tuple[ValidationLayer, ...]
    failed_layers: tuple[ValidationLayer, ...]


class TaxAssuranceService:
    def assess(
        self,
        reports: tuple[TaxDeclarationValidationReport, ...],
        policies: tuple[TaxAssurancePolicy, ...],
    ) -> TaxAssuranceAssessment:
        checks = tuple(check for report in reports for check in report.checks)
        layer_statuses = _layer_statuses(checks)
        selected = None
        for policy in sorted(policies, key=lambda item: item.rank):
            if all(
                layer_statuses.get(layer) is ValidationStatus.PASSED
                for layer in policy.required_layers
            ):
                selected = policy
        passed_layers = tuple(
            layer
            for layer in ValidationLayer
            if layer_statuses.get(layer) is ValidationStatus.PASSED
        )
        if selected is None:
            baseline_layers = policies[0].required_layers if policies else ()
            return TaxAssuranceAssessment(
                level="not_assessable",
                policy_id=None,
                policy_version=None,
                description="Les controles minimaux ne sont pas tous valides.",
                passed_layers=passed_layers,
                missing_layers=tuple(
                    layer
                    for layer in baseline_layers
                    if layer_statuses.get(layer)
                    not in {ValidationStatus.PASSED, ValidationStatus.FAILED}
                ),
                failed_layers=tuple(
                    layer
                    for layer in baseline_layers
                    if layer_statuses.get(layer) is ValidationStatus.FAILED
                ),
            )
        next_policy = next(
            (policy for policy in policies if policy.rank == selected.rank + 1),
            None,
        )
        missing_layers = (
            tuple(
                layer
                for layer in next_policy.required_layers
                if layer_statuses.get(layer) is not ValidationStatus.PASSED
            )
            if next_policy is not None
            else ()
        )
        return TaxAssuranceAssessment(
            level=selected.level,
            policy_id=selected.policy_id,
            policy_version=selected.version,
            description=selected.description,
            passed_layers=passed_layers,
            missing_layers=missing_layers,
            failed_layers=tuple(
                layer
                for layer, status in layer_statuses.items()
                if status is ValidationStatus.FAILED
            ),
        )


def _layer_statuses(
    checks: tuple[ValidationCheck, ...],
) -> dict[ValidationLayer, ValidationStatus]:
    by_layer: dict[ValidationLayer, list[ValidationStatus]] = {}
    for check in checks:
        by_layer.setdefault(check.layer, []).append(check.status)
    statuses: dict[ValidationLayer, ValidationStatus] = {}
    for layer, values in by_layer.items():
        if any(value is ValidationStatus.FAILED for value in values):
            statuses[layer] = ValidationStatus.FAILED
        elif any(value is ValidationStatus.NOT_EVALUATED for value in values):
            statuses[layer] = ValidationStatus.NOT_EVALUATED
        else:
            statuses[layer] = ValidationStatus.PASSED
    return statuses
