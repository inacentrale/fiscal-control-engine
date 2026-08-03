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
from app.tax_declaration.vat_historical_validation import VatHistoricalValidator
from app.tax_declaration.vat_tabular_extractor import VatTabularExtractor


def test_reconciles_credit_between_consecutive_periods(tmp_path: Path) -> None:
    previous = _declaration(
        tmp_path,
        "previous.csv",
        "Code;Nature;Montant\nvat_credit_carry_forward;Credit;250\n",
    )
    current = _declaration(
        tmp_path,
        "current.csv",
        "Code;Nature;Montant\n21;Credit precedent;250\n",
    )

    report = VatHistoricalValidator().validate(
        current,
        previous,
        (_rule(),),
        current_period_end=date(2025, 1, 31),
        previous_period_end=date(2024, 12, 31),
    )

    assert report.overall_status is OverallValidationStatus.PASSED
    assert report.checks[1].status is ValidationStatus.PASSED
    assert report.checks[1].difference == Decimal("0")


def test_reports_credit_difference(tmp_path: Path) -> None:
    previous = _declaration(
        tmp_path,
        "previous.csv",
        "Code;Nature;Montant\nvat_credit_carry_forward;Credit;250\n",
    )
    current = _declaration(
        tmp_path,
        "current.csv",
        "Code;Nature;Montant\n21;Credit precedent;200\n",
    )

    report = VatHistoricalValidator().validate(
        current,
        previous,
        (_rule(),),
        current_period_end=date(2025, 1, 31),
        previous_period_end=date(2024, 12, 31),
    )

    assert report.overall_status is OverallValidationStatus.FAILED
    assert report.checks[1].difference == Decimal("-50")


def test_rejects_non_consecutive_periods(tmp_path: Path) -> None:
    declaration = _declaration(
        tmp_path,
        "vat.csv",
        "Code;Nature;Montant\n21;Credit;0\n"
        "vat_credit_carry_forward;Credit;0\n",
    )

    report = VatHistoricalValidator().validate(
        declaration,
        declaration,
        (_rule(),),
        current_period_end=date(2025, 2, 28),
        previous_period_end=date(2024, 12, 31),
    )

    assert report.overall_status is OverallValidationStatus.FAILED
    assert report.checks[0].status is ValidationStatus.FAILED


def _declaration(
    tmp_path: Path,
    name: str,
    content: str,
) -> CanonicalTaxDeclaration:
    source = tmp_path / name
    source.write_text(content, encoding="utf-8")
    reference = SourceReference(
        file_name=name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )
    return VatTabularExtractor().extract(source, reference)


def _rule() -> VatValidationRule:
    return VatValidationRule(
        rule_id="credit_continuity",
        version="v1",
        layer=ValidationLayer.HISTORICAL,
        target_line="21",
        target_field="tax_amount",
        operator="carry_forward_equals",
        operand_lines=("vat_credit_carry_forward",),
        expected_value=None,
        tolerance=Decimal("0"),
        valid_from=None,
        valid_to=None,
        source_url="https://dgi.example/form.pdf",
        source_locator="lines 21 and summary",
    )
