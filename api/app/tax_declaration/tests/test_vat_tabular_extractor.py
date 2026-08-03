from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from app.tax_declaration.domain import DeclarationSourceFormat, SourceReference
from app.tax_declaration.vat_schema import VAT_SCHEMA_VERSION
from app.tax_declaration.vat_tabular_extractor import (
    VatTabularExtractionError,
    VatTabularExtractor,
)


def test_extracts_vat_lines_from_semicolon_csv(tmp_path: Path) -> None:
    source = tmp_path / "vat.csv"
    source.write_text(
        "N°;Nature des opérations;Base imposable;Taux TVA;Montant TVA\n"
        "15;Opérations courantes;1 000 000;18%;180 000\n",
        encoding="utf-8",
    )
    reference = _reference(source, DeclarationSourceFormat.CSV)

    result = VatTabularExtractor().extract(source, reference)

    assert result.schema_version == VAT_SCHEMA_VERSION
    assert len(result.records) == 1
    fields = {field.name: field for field in result.records[0].fields}
    assert fields["line_code"].normalized_value == "15"
    assert fields["tax_base"].normalized_value == Decimal("1000000")
    assert fields["tax_rate"].normalized_value == Decimal("18")
    assert fields["tax_amount"].normalized_value == Decimal("180000")
    assert fields["tax_amount"].provenance.locator.endswith("column:Montant TVA")


def test_extracts_vat_lines_from_excel(tmp_path: Path) -> None:
    source = tmp_path / "vat.xlsx"
    pd.DataFrame(
        {
            "Code": [20],
            "Libellé": ["TVA déductible"],
            "Montant": ["25 000,50"],
        },
    ).to_excel(source, index=False, engine="openpyxl")
    reference = _reference(source, DeclarationSourceFormat.EXCEL)

    result = VatTabularExtractor().extract(source, reference)

    fields = {field.name: field for field in result.records[0].fields}
    assert fields["line_code"].normalized_value == "20"
    assert fields["tax_amount"].normalized_value == Decimal("25000.50")


def test_marks_invalid_amount_as_unresolved_without_guessing(tmp_path: Path) -> None:
    source = tmp_path / "vat.csv"
    source.write_text("Nature;Montant\nVentes;inconnu\n", encoding="utf-8")
    reference = _reference(source, DeclarationSourceFormat.CSV)

    result = VatTabularExtractor().extract(source, reference)

    fields = {field.name: field for field in result.records[0].fields}
    assert fields["tax_amount"].normalized_value is None
    assert fields["tax_amount"].status.value == "unresolved"
    assert fields["tax_amount"].source_value == "inconnu"


def test_rejects_unresolved_tabular_structure(tmp_path: Path) -> None:
    source = tmp_path / "vat.csv"
    source.write_text("Colonne A;Colonne B\n1;2\n", encoding="utf-8")
    reference = _reference(source, DeclarationSourceFormat.CSV)

    with pytest.raises(VatTabularExtractionError, match="structure is unresolved"):
        VatTabularExtractor().extract(source, reference)


def _reference(path: Path, source_format: DeclarationSourceFormat) -> SourceReference:
    return SourceReference(
        file_name=path.name,
        source_format=source_format,
        content_type=None,
        content_sha256="a" * 64,
    )
