from app.tax_declaration.assurance_policy import TaxAssurancePolicy
from app.tax_declaration.assurance_service import TaxAssuranceService
from app.tax_declaration.domain import TaxDeclarationType
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationLayer,
    ValidationSeverity,
    ValidationStatus,
)


def test_assigns_limited_assurance_without_external_evidence() -> None:
    assessment = TaxAssuranceService().assess(
        (_report(*_core_layers()),),
        _policies(),
    )

    assert assessment.level == "limited"
    assert assessment.missing_layers == (
        ValidationLayer.HISTORICAL,
        ValidationLayer.RECONCILIATION,
    )


def test_assigns_reinforced_assurance_with_history_and_ledger() -> None:
    assessment = TaxAssuranceService().assess(
        (
            _report(*_core_layers()),
            _report(ValidationLayer.HISTORICAL, ValidationLayer.RECONCILIATION),
        ),
        _policies(),
    )

    assert assessment.level == "reinforced"
    assert assessment.missing_layers == (
        ValidationLayer.SUPPORTING_DOCUMENTS,
        ValidationLayer.PAYMENT_RECONCILIATION,
    )


def test_assigns_high_assurance_only_with_all_evidence_layers() -> None:
    assessment = TaxAssuranceService().assess(
        (
            _report(*_core_layers()),
            _report(
                ValidationLayer.HISTORICAL,
                ValidationLayer.RECONCILIATION,
                ValidationLayer.SUPPORTING_DOCUMENTS,
                ValidationLayer.PAYMENT_RECONCILIATION,
            ),
        ),
        _policies(),
    )

    assert assessment.level == "high"
    assert assessment.missing_layers == ()


def test_returns_not_assessable_when_core_layer_is_unresolved() -> None:
    report = _report(*_core_layers())
    checks = tuple(
        ValidationCheck(
            check_id=check.check_id,
            layer=check.layer,
            status=(
                ValidationStatus.NOT_EVALUATED
                if check.layer is ValidationLayer.FISCAL
                else check.status
            ),
            severity=check.severity,
            message=check.message,
        )
        for check in report.checks
    )

    assessment = TaxAssuranceService().assess(
        (
            TaxDeclarationValidationReport(
                overall_status=OverallValidationStatus.INCOMPLETE,
                checks=checks,
            ),
        ),
        _policies(),
    )

    assert assessment.level == "not_assessable"
    assert assessment.missing_layers == (ValidationLayer.FISCAL,)


def _core_layers() -> tuple[ValidationLayer, ...]:
    return (
        ValidationLayer.STRUCTURE,
        ValidationLayer.COMPLETENESS,
        ValidationLayer.ARITHMETIC,
        ValidationLayer.FISCAL,
    )


def _report(*layers: ValidationLayer) -> TaxDeclarationValidationReport:
    return TaxDeclarationValidationReport(
        overall_status=OverallValidationStatus.PASSED,
        checks=tuple(
            ValidationCheck(
                check_id=f"check_{layer.value}",
                layer=layer,
                status=ValidationStatus.PASSED,
                severity=ValidationSeverity.INFO,
                message="passed",
            )
            for layer in layers
        ),
    )


def _policies() -> tuple[TaxAssurancePolicy, ...]:
    core = _core_layers()
    return (
        TaxAssurancePolicy(
            "limited",
            "v1",
            "limited",
            1,
            core,
            "Limited",
            TaxDeclarationType.VAT,
        ),
        TaxAssurancePolicy(
            "reinforced",
            "v1",
            "reinforced",
            2,
            (*core, ValidationLayer.HISTORICAL, ValidationLayer.RECONCILIATION),
            "Reinforced",
            TaxDeclarationType.VAT,
        ),
        TaxAssurancePolicy(
            "high",
            "v1",
            "high",
            3,
            (
                *core,
                ValidationLayer.HISTORICAL,
                ValidationLayer.RECONCILIATION,
                ValidationLayer.SUPPORTING_DOCUMENTS,
                ValidationLayer.PAYMENT_RECONCILIATION,
            ),
            "High",
            TaxDeclarationType.VAT,
        ),
    )
