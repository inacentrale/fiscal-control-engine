from datetime import date
from decimal import Decimal
from pathlib import Path

from app.tax_declaration.corporate_income_tax_rule_loader import (
    load_corporate_income_tax_validation_rules,
)
from app.tax_declaration.corporate_income_tax_tabular_extractor import (
    CorporateIncomeTaxTabularExtractor,
)
from app.tax_declaration.corporate_income_tax_validation_service import (
    CorporateIncomeTaxDeclarationValidator,
)
from app.tax_declaration.domain import (
    CanonicalTaxDeclaration,
    DeclarationSourceFormat,
    SourceReference,
)
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationStatus,
)

_HEADER = (
    "IFU;Raison sociale;Regime;Benefice imposable;CA annuel HT;"
    "IS calcule;IMFPIC;Traitement IMFPIC;IS a payer\n"
)


def test_validates_is_rate_and_minimum_floor(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Societe Test;Reel Normal;10000000;400099999;"
        "2750000;2000000;Standard;2750000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    rate = _check(report, "corporate_income_tax_rate_1")
    minimum = _check(report, "corporate_income_tax_minimum_1")
    deadline = _check(report, "corporate_income_tax_deadline")
    assert report.overall_status is OverallValidationStatus.PASSED
    assert rate.status is ValidationStatus.PASSED
    assert rate.expected_value == Decimal("2750000")
    assert rate.source_locator == "article 87"
    assert minimum.status is ValidationStatus.PASSED
    assert minimum.expected_value == Decimal("2000000")
    assert minimum.actual_value == Decimal("2000000")
    assert minimum.source_locator == "articles 88 et 89"
    assert deadline.status is ValidationStatus.PASSED
    assert deadline.expected_date == date(2026, 4, 30)


def test_reports_incorrect_is_rate(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Societe Test;Reel Normal;10000000;400000000;"
        "2700000;2000000;Standard;2700000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    rate = _check(report, "corporate_income_tax_rate_1")
    assert report.overall_status is OverallValidationStatus.FAILED
    assert rate.status is ValidationStatus.FAILED
    assert rate.expected_value == Decimal("2750000")
    assert rate.difference == Decimal("-50000")


def test_reports_incorrect_minimum_tax_amount(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Petite Societe;Reel Normal;500000;30099999;"
        "137500;137500;Standard;137500\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    rate = _check(report, "corporate_income_tax_rate_1")
    minimum = _check(report, "corporate_income_tax_minimum_1")
    assert report.overall_status is OverallValidationStatus.FAILED
    assert rate.status is ValidationStatus.PASSED
    assert minimum.status is ValidationStatus.FAILED
    assert minimum.expected_value == Decimal("1000000")
    assert minimum.actual_value == Decimal("137500")
    assert minimum.difference == Decimal("-862500")


def test_rounds_turnover_down_to_hundred_thousand_for_imfpic(
    tmp_path: Path,
) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Societe Test;Reel Normal;5000000;250099999;"
        "1375000;1250000;Standard;1375000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    minimum = _check(report, "corporate_income_tax_minimum_1")
    assert minimum.status is ValidationStatus.PASSED
    assert minimum.expected_value == Decimal("1250000")
    assert minimum.difference == Decimal("0")


def test_applies_simplified_regime_floor_after_proportional_calculation(
    tmp_path: Path,
) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Petite Societe;Reel Simplifie;500000;20099999;"
        "137500;300000;Standard;300000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    minimum = _check(report, "corporate_income_tax_minimum_1")
    assert minimum.status is ValidationStatus.PASSED
    assert minimum.expected_value == Decimal("300000")


def test_does_not_apply_standard_imfpic_without_explicit_treatment(
    tmp_path: Path,
) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Societe Test;Reel Normal;10000000;400000000;"
        "2750000;2000000;;2750000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    minimum = _check(report, "corporate_income_tax_minimum_1")
    assert minimum.status is ValidationStatus.NOT_EVALUATED
    assert report.overall_status is OverallValidationStatus.INCOMPLETE


def test_applies_floor_only_for_exclusive_activity(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Station Test;Reel Normal;10000000;900000000;"
        "2750000;1000000;Plancher uniquement;2750000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    minimum = _check(report, "corporate_income_tax_minimum_1")
    assert minimum.status is ValidationStatus.PASSED
    assert minimum.expected_value == Decimal("1000000")


def test_applies_approved_management_center_reduction(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Societe CGA;Reel Normal;10000000;800000000;"
        "2750000;2000000;CGA;2750000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    minimum = _check(report, "corporate_income_tax_minimum_1")
    assert minimum.status is ValidationStatus.PASSED
    assert minimum.expected_value == Decimal("2000000")


def test_combines_cga_reduction_with_exclusive_activity_floor(
    tmp_path: Path,
) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Station CGA;Reel Normal;10000000;900000000;"
        "2750000;500000;CGA et activite exclusive;2750000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    minimum = _check(report, "corporate_income_tax_minimum_1")
    assert minimum.status is ValidationStatus.PASSED
    assert minimum.expected_value == Decimal("500000")


def test_exempts_new_company_first_exercise_without_turnover(
    tmp_path: Path,
) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Societe Nouvelle;Reel Normal;10000000;;"
        "2750000;0;Premier exercice;2750000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 4, 30),
    )

    minimum = _check(report, "corporate_income_tax_minimum_1")
    assert minimum.status is ValidationStatus.PASSED
    assert minimum.expected_value == Decimal("0")
    assert minimum.source_locator == "articles 88 et 89; article 90"


def test_reports_late_annual_filing(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Societe Test;Reel Normal;10000000;400000000;"
        "2750000;2000000;Standard;2750000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 5, 2),
    )

    deadline = _check(report, "corporate_income_tax_deadline")
    assert report.overall_status is OverallValidationStatus.FAILED
    assert deadline.status is ValidationStatus.FAILED
    assert deadline.expected_date == date(2026, 4, 30)


def test_does_not_guess_deadline_for_non_december_fiscal_year(
    tmp_path: Path,
) -> None:
    declaration = _declaration(
        tmp_path,
        "0123456789;Societe Test;Reel Normal;10000000;400000000;"
        "2750000;2000000;Standard;2750000\n",
    )

    report = _validate(
        declaration,
        period_end=date(2025, 6, 30),
        filing_date=date(2025, 10, 30),
    )

    assert report.overall_status is OverallValidationStatus.INCOMPLETE
    assert (
        _check(report, "corporate_income_tax_deadline").status
        is ValidationStatus.NOT_EVALUATED
    )


def _declaration(tmp_path: Path, row: str) -> CanonicalTaxDeclaration:
    source = tmp_path / "is.csv"
    source.write_text(_HEADER + row, encoding="utf-8")
    reference = SourceReference(
        file_name=source.name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )
    return CorporateIncomeTaxTabularExtractor().extract(source, reference)


def _validate(
    declaration: CanonicalTaxDeclaration,
    *,
    period_end: date,
    filing_date: date,
) -> TaxDeclarationValidationReport:
    return CorporateIncomeTaxDeclarationValidator().validate(
        declaration,
        load_corporate_income_tax_validation_rules(_rules_path()),
        period_end=period_end,
        filing_date=filing_date,
    )


def _check(
    report: TaxDeclarationValidationReport,
    check_id: str,
) -> ValidationCheck:
    return next(check for check in report.checks if check.check_id == check_id)


def _rules_path() -> Path:
    return (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "bf-is-validation-rules.csv"
    )
