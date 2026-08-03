from datetime import date
from decimal import Decimal
from pathlib import Path

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
from app.tax_declaration.withholding_deadline_loader import (
    load_withholding_deadline_rules,
)
from app.tax_declaration.withholding_rule_loader import (
    load_withholding_validation_rules,
)
from app.tax_declaration.withholding_tabular_extractor import (
    WithholdingTabularExtractor,
)
from app.tax_declaration.withholding_validation_service import (
    WithholdingDeclarationValidator,
)


def test_validates_resident_standard_rate_and_amount(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;resident;registered_standard;Standard;1000000;1000000;5;50000\n",
    )

    report = _validate(declaration, date(2024, 12, 31))

    assert report.overall_status is OverallValidationStatus.PASSED
    assert _check(report, "withholding_rate_01").status is ValidationStatus.PASSED
    amount = _check(report, "withholding_amount_01")
    assert amount.status is ValidationStatus.PASSED
    assert amount.expected_value == Decimal("50000")
    assert amount.actual_value == Decimal("50000")
    assert amount.source_locator == "article 16 / CGI article 207"


def test_applies_2025_temporary_work_rule_only_in_2025(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;resident;temporary_work_company;Interim;1000000;1000000;2;20000\n",
    )

    report_2025 = _validate(declaration, date(2025, 12, 31))
    report_2026 = _validate(declaration, date(2026, 1, 1))

    assert report_2025.overall_status is OverallValidationStatus.PASSED
    assert report_2026.overall_status is OverallValidationStatus.INCOMPLETE
    assert (
        _check(report_2026, "withholding_rule_01").status
        is ValidationStatus.NOT_EVALUATED
    )


def test_applies_narrower_2026_staffing_service_category(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;resident;temporary_staffing_service;Mise a disposition;"
        "1000000;1000000;2;20000\n",
    )

    report = _validate(declaration, date(2026, 1, 1))

    assert report.overall_status is OverallValidationStatus.PASSED
    assert _check(report, "withholding_rate_01").source_locator == (
        "article 15 / CGI article 207"
    )


def test_reports_rate_and_amount_differences(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;resident;registered_standard;Standard;1000000;1000000;2;21000\n",
    )

    report = _validate(declaration, date(2024, 12, 31))

    rate = _check(report, "withholding_rate_01")
    amount = _check(report, "withholding_amount_01")
    assert report.overall_status is OverallValidationStatus.FAILED
    assert rate.expected_value == Decimal("5")
    assert rate.actual_value == Decimal("2")
    assert rate.difference == Decimal("-3")
    assert amount.expected_value == Decimal("50000")
    assert amount.actual_value == Decimal("21000")
    assert amount.difference == Decimal("-29000")


def test_requires_explicit_regime_and_rate_category(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;;;Standard;1000000;1000000;5;50000\n",
    )

    report = _validate(declaration, date(2024, 12, 31))

    assert report.overall_status is OverallValidationStatus.INCOMPLETE
    assert (
        _check(report, "withholding_completeness").status
        is ValidationStatus.NOT_EVALUATED
    )
    assert (
        _check(report, "withholding_rule_01").status
        is ValidationStatus.NOT_EVALUATED
    )


def test_does_not_extend_expired_non_determined_20_percent_rule(
    tmp_path: Path,
) -> None:
    declaration = _declaration(
        tmp_path,
        "01;non_determined;other_legal_entity;Personne morale;"
        "1000000;1000000;20;200000\n",
    )

    report_2024 = _validate(declaration, date(2024, 12, 31))
    report_2025 = _validate(declaration, date(2025, 1, 1))

    assert report_2024.overall_status is OverallValidationStatus.PASSED
    assert report_2025.overall_status is OverallValidationStatus.INCOMPLETE


def test_uses_payment_amount_for_nonresident_standard(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;nonresident;standard_no_treaty_override;Conseil;"
        "2000000;;20;400000\n",
    )

    report = _validate(declaration, date(2026, 1, 1))

    amount = _check(report, "withholding_amount_01")
    assert report.overall_status is OverallValidationStatus.PASSED
    assert amount.expected_value == Decimal("400000")
    assert amount.source_locator == "articles 210 a 214 / article 212"


def test_missing_period_prevents_rule_selection(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;resident;registered_standard;Standard;1000000;1000000;5;50000\n",
    )

    report = WithholdingDeclarationValidator().validate(
        declaration,
        load_withholding_validation_rules(_rules_path()),
        period_end=None,
    )

    assert report.overall_status is OverallValidationStatus.INCOMPLETE
    assert _check(report, "withholding_rule_period").status is (
        ValidationStatus.NOT_EVALUATED
    )


def test_validates_next_month_deadline_across_year_end(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;resident;registered_standard;Standard;1000000;1000000;5;50000\n",
    )

    report = WithholdingDeclarationValidator().validate(
        declaration,
        load_withholding_validation_rules(_rules_path()),
        period_end=date(2024, 12, 31),
        filing_date=date(2025, 1, 15),
        deadline_rules=load_withholding_deadline_rules(_deadline_rules_path()),
    )

    check = _check(report, "withholding_deadline_resident")
    assert report.overall_status is OverallValidationStatus.PASSED
    assert check.status is ValidationStatus.PASSED
    assert check.expected_date == date(2025, 1, 15)
    assert check.actual_date == date(2025, 1, 15)
    assert check.source_locator == "article 208"


def test_reports_late_nonresident_filing(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;nonresident;standard_no_treaty_override;Conseil;"
        "2000000;;20;400000\n",
    )

    report = WithholdingDeclarationValidator().validate(
        declaration,
        load_withholding_validation_rules(_rules_path()),
        period_end=date(2026, 1, 31),
        filing_date=date(2026, 2, 16),
        deadline_rules=load_withholding_deadline_rules(_deadline_rules_path()),
    )

    check = _check(report, "withholding_deadline_nonresident")
    assert report.overall_status is OverallValidationStatus.FAILED
    assert check.status is ValidationStatus.FAILED
    assert check.expected_date == date(2026, 2, 15)
    assert check.source_locator == "article 214"


def test_missing_filing_date_keeps_deadline_not_evaluated(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "01;non_determined;manual_or_teaching;Vacation;"
        "1000000;1000000;2;20000\n",
    )

    report = WithholdingDeclarationValidator().validate(
        declaration,
        load_withholding_validation_rules(_rules_path()),
        period_end=date(2026, 1, 31),
        deadline_rules=load_withholding_deadline_rules(_deadline_rules_path()),
    )

    check = _check(report, "withholding_deadline_non_determined")
    assert report.overall_status is OverallValidationStatus.INCOMPLETE
    assert check.status is ValidationStatus.NOT_EVALUATED
    assert check.expected_date == date(2026, 2, 15)
    assert check.actual_date is None


def _declaration(tmp_path: Path, row: str) -> CanonicalTaxDeclaration:
    source = tmp_path / "ras.csv"
    source.write_text(
        "Code;Regime retenue;Categorie taux;Categorie;Montant verse;Base;"
        "Taux;Montant des retenues\n" + row,
        encoding="utf-8",
    )
    reference = SourceReference(
        file_name=source.name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )
    return WithholdingTabularExtractor().extract(source, reference)


def _validate(
    declaration: CanonicalTaxDeclaration,
    period_end: date,
) -> TaxDeclarationValidationReport:
    return WithholdingDeclarationValidator().validate(
        declaration,
        load_withholding_validation_rules(_rules_path()),
        period_end=period_end,
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
        / "bf-withholding-validation-rules.csv"
    )


def _deadline_rules_path() -> Path:
    return (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "bf-withholding-deadline-rules.csv"
    )
