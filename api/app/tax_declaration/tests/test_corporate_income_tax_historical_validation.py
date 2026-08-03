from datetime import date
from decimal import Decimal
from pathlib import Path

from app.tax_declaration.corporate_income_tax_historical_validation import (
    CorporateIncomeTaxHistoricalValidator,
)
from app.tax_declaration.corporate_income_tax_rule_loader import (
    load_corporate_income_tax_validation_rules,
)
from app.tax_declaration.corporate_income_tax_tabular_extractor import (
    CorporateIncomeTaxTabularExtractor,
)
from app.tax_declaration.domain import (
    CanonicalTaxDeclaration,
    DeclarationSourceFormat,
    SourceReference,
)
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationStatus,
)

_HEADER = (
    "IFU;Raison sociale;Regime;Benefice imposable;"
    "IS calcule;IMFPIC;IS a payer;Acomptes provisionnels verses\n"
)


def test_validates_installments_against_prior_year_due(tmp_path: Path) -> None:
    previous = _declaration(
        tmp_path,
        "previous.csv",
        "0123456789;Societe Test;Reel Normal;10000000;2750000;;2750000;\n",
    )
    current = _declaration(
        tmp_path,
        "current.csv",
        "0123456789;Societe Test;Reel Normal;11000000;3025000;;3025000;2062500\n",
    )

    report = _validate(
        current,
        previous,
        current_period_end=date(2025, 12, 31),
        previous_period_end=date(2024, 12, 31),
    )

    installments = next(
        check
        for check in report.checks
        if check.check_id == "corporate_income_tax_installments"
    )
    period = next(
        check
        for check in report.checks
        if check.check_id == "corporate_income_tax_consecutive_exercises"
    )
    assert report.overall_status is OverallValidationStatus.PASSED
    assert installments.status is ValidationStatus.PASSED
    assert installments.expected_value == Decimal("2062500")
    assert installments.difference == Decimal("0")
    assert period.status is ValidationStatus.PASSED


def test_reports_installment_difference(tmp_path: Path) -> None:
    previous = _declaration(
        tmp_path,
        "previous.csv",
        "0123456789;Societe Test;Reel Normal;10000000;2750000;;2750000;\n",
    )
    current = _declaration(
        tmp_path,
        "current.csv",
        "0123456789;Societe Test;Reel Normal;11000000;3025000;;3025000;2000000\n",
    )

    report = _validate(
        current,
        previous,
        current_period_end=date(2025, 12, 31),
        previous_period_end=date(2024, 12, 31),
    )

    installments = next(
        check
        for check in report.checks
        if check.check_id == "corporate_income_tax_installments"
    )
    assert report.overall_status is OverallValidationStatus.FAILED
    assert installments.status is ValidationStatus.FAILED
    assert installments.difference == Decimal("-62500")


def test_rejects_non_consecutive_exercises(tmp_path: Path) -> None:
    previous = _declaration(
        tmp_path,
        "previous.csv",
        "0123456789;Societe Test;Reel Normal;10000000;2750000;;2750000;\n",
    )
    current = _declaration(
        tmp_path,
        "current.csv",
        "0123456789;Societe Test;Reel Normal;11000000;3025000;;3025000;2062500\n",
    )

    report = _validate(
        current,
        previous,
        current_period_end=date(2026, 12, 31),
        previous_period_end=date(2024, 12, 31),
    )

    period = next(
        check
        for check in report.checks
        if check.check_id == "corporate_income_tax_consecutive_exercises"
    )
    assert report.overall_status is OverallValidationStatus.FAILED
    assert period.status is ValidationStatus.FAILED


def test_does_not_guess_continuity_outside_december_exercises(
    tmp_path: Path,
) -> None:
    previous = _declaration(
        tmp_path,
        "previous.csv",
        "0123456789;Societe Test;Reel Normal;10000000;2750000;;2750000;\n",
    )
    current = _declaration(
        tmp_path,
        "current.csv",
        "0123456789;Societe Test;Reel Normal;11000000;3025000;;3025000;2062500\n",
    )

    report = _validate(
        current,
        previous,
        current_period_end=date(2025, 6, 30),
        previous_period_end=date(2024, 6, 30),
    )

    period = next(
        check
        for check in report.checks
        if check.check_id == "corporate_income_tax_consecutive_exercises"
    )
    assert period.status is ValidationStatus.NOT_EVALUATED
    assert report.overall_status is OverallValidationStatus.INCOMPLETE


def _declaration(tmp_path: Path, name: str, row: str) -> CanonicalTaxDeclaration:
    source = tmp_path / name
    source.write_text(_HEADER + row, encoding="utf-8")
    reference = SourceReference(
        file_name=name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )
    return CorporateIncomeTaxTabularExtractor().extract(source, reference)


def _validate(
    current: CanonicalTaxDeclaration,
    previous: CanonicalTaxDeclaration,
    *,
    current_period_end: date,
    previous_period_end: date,
) -> TaxDeclarationValidationReport:
    return CorporateIncomeTaxHistoricalValidator().validate(
        current,
        previous,
        load_corporate_income_tax_validation_rules(_rules_path()),
        current_period_end=current_period_end,
        previous_period_end=previous_period_end,
    )


def _rules_path() -> Path:
    return (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "bf-is-validation-rules.csv"
    )
