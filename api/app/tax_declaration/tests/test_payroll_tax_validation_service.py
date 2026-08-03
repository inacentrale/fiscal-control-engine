from datetime import date
from pathlib import Path

from app.tax_declaration.domain import (
    CanonicalTaxDeclaration,
    DeclarationSourceFormat,
    SourceReference,
)
from app.tax_declaration.payroll_tax_rule_loader import (
    load_payroll_tax_validation_rules,
)
from app.tax_declaration.payroll_tax_tabular_extractor import (
    PayrollTaxTabularExtractor,
)
from app.tax_declaration.payroll_tax_validation_service import (
    PayrollTaxDeclarationValidator,
)
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
    ValidationCheck,
    ValidationStatus,
)


def test_validates_progressive_iuts_and_family_reduction(tmp_path: Path) -> None:
    declaration = _declaration(tmp_path, "01;Salarie Test;350000;280000;2;42237\n")

    report = _validate(
        declaration,
        period_end=date(2026, 1, 31),
        filing_date=date(2026, 2, 10),
    )

    amount = _check(report, "payroll_tax_amount_01")
    deadline = _check(report, "payroll_tax_deadline")
    assert report.overall_status is OverallValidationStatus.PASSED
    assert amount.status is ValidationStatus.PASSED
    assert amount.expected_value == 42237
    assert amount.actual_value == 42237
    assert amount.source_locator == "article 112; article 113"
    assert deadline.status is ValidationStatus.PASSED
    assert deadline.expected_date == date(2026, 2, 10)


def test_reports_incorrect_iuts_amount(tmp_path: Path) -> None:
    declaration = _declaration(tmp_path, "01;Salarie Test;350000;280000;2;42000\n")

    report = _validate(
        declaration,
        period_end=date(2026, 1, 31),
        filing_date=date(2026, 2, 10),
    )

    amount = _check(report, "payroll_tax_amount_01")
    assert report.overall_status is OverallValidationStatus.FAILED
    assert amount.status is ValidationStatus.FAILED
    assert amount.expected_value == 42237
    assert amount.difference == -237


def test_validates_year_end_deadline(tmp_path: Path) -> None:
    declaration = _declaration(tmp_path, "01;Salarie Test;50000;50000;0;2420\n")

    report = _validate(
        declaration,
        period_end=date(2025, 12, 31),
        filing_date=date(2026, 1, 10),
    )

    assert _check(report, "payroll_tax_deadline").expected_date == date(2026, 1, 10)
    assert report.overall_status is OverallValidationStatus.PASSED


def test_reports_late_filing_above_small_withholding_threshold(
    tmp_path: Path,
) -> None:
    declaration = _declaration(tmp_path, "01;Salarie Test;280000;280000;0;46930\n")

    report = _validate(
        declaration,
        period_end=date(2026, 1, 31),
        filing_date=date(2026, 2, 11),
    )

    assert report.overall_status is OverallValidationStatus.FAILED
    assert _check(report, "payroll_tax_deadline").status is ValidationStatus.FAILED


def test_does_not_guess_optional_semester_deadline(tmp_path: Path) -> None:
    declaration = _declaration(tmp_path, "01;Salarie Test;50000;50000;0;2420\n")

    report = _validate(
        declaration,
        period_end=date(2026, 1, 31),
        filing_date=date(2026, 2, 11),
    )

    assert report.overall_status is OverallValidationStatus.INCOMPLETE
    assert (
        _check(report, "payroll_tax_deadline").status
        is ValidationStatus.NOT_EVALUATED
    )


def _declaration(tmp_path: Path, row: str) -> CanonicalTaxDeclaration:
    source = tmp_path / "iuts.csv"
    source.write_text(
        "N ordre;Nom du salarie;Salaire brut;Base imposable;"
        "Nombre de charges;IUTS\n" + row,
        encoding="utf-8",
    )
    reference = SourceReference(
        file_name=source.name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )
    return PayrollTaxTabularExtractor().extract(source, reference)


def _validate(
    declaration: CanonicalTaxDeclaration,
    *,
    period_end: date,
    filing_date: date,
) -> TaxDeclarationValidationReport:
    return PayrollTaxDeclarationValidator().validate(
        declaration,
        load_payroll_tax_validation_rules(_rules_path()),
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
        / "bf-iuts-validation-rules.csv"
    )
