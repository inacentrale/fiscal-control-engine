from decimal import Decimal
from pathlib import Path

import pytest

from app.tax_declaration.domain import (
    DeclarationSourceFormat,
    ResolutionStatus,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.ingestion_service import TaxDeclarationIngestionService
from app.tax_declaration.withholding_schema import WITHHOLDING_SCHEMA_VERSION
from app.tax_declaration.withholding_tabular_extractor import (
    WithholdingTabularExtractionError,
    WithholdingTabularExtractor,
)


def test_extracts_withholding_lines_without_inferring_regime(tmp_path: Path) -> None:
    source = tmp_path / "ras.csv"
    source.write_text(
        "N;Categorie;Montant des paiements bruts TTC;Base;"
        "Taux de la retenue;Montant des retenues\n"
        "01;Prestations;1 180 000;1 000 000;2%;20 000\n",
        encoding="utf-8",
    )

    declaration = WithholdingTabularExtractor().extract(
        source,
        _reference(source),
    )

    assert declaration.schema_version == WITHHOLDING_SCHEMA_VERSION
    assert declaration.declaration_type is TaxDeclarationType.WITHHOLDING_TAX
    assert declaration.fields == ()
    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["line_code"].normalized_value == "01"
    assert fields["payment_amount"].normalized_value == Decimal("1180000")
    assert fields["tax_base"].normalized_value == Decimal("1000000")
    assert fields["tax_rate"].normalized_value == Decimal("2")
    assert fields["withheld_amount"].normalized_value == Decimal("20000")
    assert "withholding_regime" not in fields


def test_keeps_invalid_withheld_amount_unresolved(tmp_path: Path) -> None:
    source = tmp_path / "ras.csv"
    source.write_text(
        "Categorie;Taux;Montant des retenues\nPrestations;2%;inconnu\n",
        encoding="utf-8",
    )

    declaration = WithholdingTabularExtractor().extract(source, _reference(source))

    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["withheld_amount"].normalized_value is None
    assert fields["withheld_amount"].status is ResolutionStatus.UNRESOLVED
    assert fields["withheld_amount"].source_value == "inconnu"


def test_detects_partner_nif_without_value_format_assumption(tmp_path: Path) -> None:
    source = tmp_path / "ras-nif.csv"
    source.write_text(
        "N;NIF;Prestataire;Categorie;Taux;Montant des retenues\n"
        "01;00-AZ-19;Partenaire Test;Prestations;2%;20000\n",
        encoding="utf-8",
    )

    declaration = WithholdingTabularExtractor().extract(source, _reference(source))

    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["partner_identifier"].normalized_value == "00-AZ-19"
    assert fields["partner_identifier_type"].normalized_value == "NIF"
    assert fields["partner_name"].normalized_value == "Partenaire Test"


def test_rejects_table_without_withholding_amount(tmp_path: Path) -> None:
    source = tmp_path / "ras.csv"
    source.write_text("Categorie;Taux\nPrestations;2%\n", encoding="utf-8")

    with pytest.raises(
        WithholdingTabularExtractionError,
        match="structure is unresolved",
    ):
        WithholdingTabularExtractor().extract(source, _reference(source))


def test_ingestion_auto_detects_strong_withholding_headers(tmp_path: Path) -> None:
    source = tmp_path / "unknown.upload"
    source.write_text(
        "Categorie;Taux de la retenue;Montant des retenues\n"
        "Prestations;2%;20000\n",
        encoding="utf-8",
    )

    result = TaxDeclarationIngestionService().ingest(source)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.declaration_type is TaxDeclarationType.WITHHOLDING_TAX
    assert result.declaration is not None


def test_explicit_type_resolves_ambiguous_generic_headers(tmp_path: Path) -> None:
    source = tmp_path / "ras.csv"
    source.write_text(
        "Libelle;Taux;Montant\nPrestations;2%;20000\n",
        encoding="utf-8",
    )

    result = TaxDeclarationIngestionService().ingest(
        source,
        expected_type=TaxDeclarationType.WITHHOLDING_TAX,
    )

    assert result.status is ResolutionStatus.UNRESOLVED
    assert result.reason == "structure_unresolved"


def _reference(path: Path) -> SourceReference:
    return SourceReference(
        file_name=path.name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )
