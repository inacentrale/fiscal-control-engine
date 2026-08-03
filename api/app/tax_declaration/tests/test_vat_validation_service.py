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
    ValidationLayer,
    ValidationStatus,
    VatValidationRule,
)
from app.tax_declaration.vat_tabular_extractor import VatTabularExtractor
from app.tax_declaration.vat_validation_service import VatDeclarationValidator


def test_passes_when_declared_total_matches_source_lines(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "Code;Nature;Montant\n01;Ventes;100\n02;Services;50\n14;Total;150\n",
    )

    report = VatDeclarationValidator().validate(declaration, (_rule(),))

    assert report.overall_status is OverallValidationStatus.PASSED
    check = next(check for check in report.checks if check.check_id == "r14")
    assert check.status is ValidationStatus.PASSED
    assert check.difference == Decimal("0")


def test_fails_and_reconciles_difference_when_total_is_wrong(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "Code;Nature;Montant\n01;Ventes;100\n02;Services;50\n14;Total;140\n",
    )

    report = VatDeclarationValidator().validate(declaration, (_rule(),))

    assert report.overall_status is OverallValidationStatus.FAILED
    check = next(check for check in report.checks if check.check_id == "r14")
    assert check.expected_value == Decimal("150")
    assert check.actual_value == Decimal("140")
    assert check.difference == Decimal("-10")


def test_does_not_treat_missing_lines_as_zero(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "Code;Nature;Montant\n01;Ventes;100\n14;Total;100\n",
    )

    report = VatDeclarationValidator().validate(declaration, (_rule(),))

    assert report.overall_status is OverallValidationStatus.INCOMPLETE
    check = next(check for check in report.checks if check.check_id == "r14")
    assert check.status is ValidationStatus.NOT_EVALUATED
    assert check.affected_lines == ("02",)


def test_fails_structure_on_duplicate_line_codes(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "Code;Nature;Montant\n01;Ventes;100\n01;Ventes;100\n14;Total;200\n",
    )

    report = VatDeclarationValidator().validate(declaration, (_rule(),))

    assert report.overall_status is OverallValidationStatus.FAILED
    assert report.checks[0].status is ValidationStatus.FAILED
    assert report.checks[0].affected_lines == ("01",)


def test_validates_fiscal_rate_for_applicable_period(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "Code;Nature;Taux;Montant\n15;Taux normal;18%;180\n",
    )
    rule = _equals_rule()

    report = VatDeclarationValidator().validate(
        declaration,
        (rule,),
        period_end=date(2024, 12, 31),
    )

    check = next(check for check in report.checks if check.check_id == "rate18")
    assert check.status is ValidationStatus.PASSED
    assert check.expected_value == Decimal("18")


def test_does_not_apply_dated_fiscal_rule_without_period(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "Code;Nature;Taux;Montant\n15;Taux normal;18%;180\n",
    )

    report = VatDeclarationValidator().validate(declaration, (_equals_rule(),))

    check = next(check for check in report.checks if check.check_id == "rate18")
    assert check.status is ValidationStatus.NOT_EVALUATED
    assert report.overall_status is OverallValidationStatus.INCOMPLETE


def test_validates_monthly_filing_deadline(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "Code;Nature;Montant\n01;Ventes;100\n",
    )

    report = VatDeclarationValidator().validate(
        declaration,
        (_deadline_rule(),),
        period_end=date(2024, 12, 31),
        filing_date=date(2025, 1, 15),
    )

    check = next(check for check in report.checks if check.check_id == "deadline")
    assert check.status is ValidationStatus.PASSED
    assert check.expected_date == date(2025, 1, 15)


def test_fails_late_monthly_filing(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "Code;Nature;Montant\n01;Ventes;100\n",
    )

    report = VatDeclarationValidator().validate(
        declaration,
        (_deadline_rule(),),
        period_end=date(2024, 12, 31),
        filing_date=date(2025, 1, 16),
    )

    check = next(check for check in report.checks if check.check_id == "deadline")
    assert check.status is ValidationStatus.FAILED
    assert check.actual_date == date(2025, 1, 16)


def _declaration(tmp_path: Path, content: str) -> CanonicalTaxDeclaration:
    source = tmp_path / "vat.csv"
    source.write_text(content, encoding="utf-8")
    reference = SourceReference(
        file_name=source.name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )
    return VatTabularExtractor().extract(source, reference)


def _rule() -> VatValidationRule:
    return VatValidationRule(
        rule_id="r14",
        version="v1",
        layer=ValidationLayer.ARITHMETIC,
        target_line="14",
        target_field="tax_amount",
        operator="sum",
        operand_lines=("01", "02"),
        expected_value=None,
        tolerance=Decimal("0"),
        valid_from=None,
        valid_to=None,
        source_url="https://dgi.example/form.pdf",
        source_locator="line 14",
    )


def _equals_rule() -> VatValidationRule:
    return VatValidationRule(
        rule_id="rate18",
        version="v1",
        layer=ValidationLayer.FISCAL,
        target_line="15",
        target_field="tax_rate",
        operator="equals",
        operand_lines=(),
        expected_value=Decimal("18"),
        tolerance=Decimal("0"),
        valid_from=date(2020, 4, 1),
        valid_to=None,
        source_url="https://dgi.example/cgi",
        source_locator="article 317",
    )


def _deadline_rule() -> VatValidationRule:
    return VatValidationRule(
        rule_id="deadline",
        version="v1",
        layer=ValidationLayer.FISCAL,
        target_line="",
        target_field="",
        operator="monthly_deadline",
        operand_lines=(),
        expected_value=None,
        tolerance=Decimal("0"),
        valid_from=date(2023, 1, 1),
        valid_to=None,
        source_url="https://dgi.example/cgi",
        source_locator="article 334",
    )
