from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.tax_declaration.corporate_income_tax_schema import (
    BURKINA_FASO_CORPORATE_INCOME_TAX_SCHEMA,
    CORPORATE_INCOME_TAX_OFFICIAL_FORM_URLS,
)
from app.tax_declaration.corporate_income_tax_tabular_extractor import (
    CorporateIncomeTaxTabularExtractor,
)
from app.tax_declaration.domain import (
    DeclarationSourceFormat,
    ResolutionStatus,
    SourceReference,
    TaxDeclarationType,
)

_HEADER = (
    "IFU;Raison sociale;Regime;Benefice imposable;"
    "IS calcule;IMFPIC;IS a payer\n"
)


def test_schema_is_sourced_from_official_dgi_forms() -> None:
    schema = BURKINA_FASO_CORPORATE_INCOME_TAX_SCHEMA

    assert schema.version == "bf.is.v1"
    assert schema.declaration_type is TaxDeclarationType.CORPORATE_INCOME_TAX
    assert schema.official_source_urls == CORPORATE_INCOME_TAX_OFFICIAL_FORM_URLS
    assert all(
        url.startswith("https://dgi.bf/") for url in schema.official_source_urls
    )
    assert schema.record_fields == (
        "company_identifier",
        "company_identifier_type",
        "company_name",
        "tax_regime",
        "taxable_profit",
        "annual_turnover_excluding_tax",
        "computed_corporate_tax",
        "minimum_tax_declared",
        "minimum_tax_treatment",
        "corporate_tax_due",
        "provisional_installments_paid",
    )


def test_extracts_official_is_columns_from_csv(tmp_path: Path) -> None:
    source = tmp_path / "is.csv"
    source.write_text(
        _HEADER + "0123456789;Societe Test;Reel Normal;10000000;2750000;;2750000\n",
        encoding="utf-8",
    )
    reference = _reference(source, DeclarationSourceFormat.CSV)

    declaration = CorporateIncomeTaxTabularExtractor().extract(source, reference)

    assert declaration.declaration_type is TaxDeclarationType.CORPORATE_INCOME_TAX
    assert declaration.schema_version == "bf.is.v1"
    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["company_identifier"].normalized_value == "0123456789"
    assert fields["company_identifier_type"].normalized_value == "IFU"
    assert fields["company_name"].normalized_value == "Societe Test"
    assert fields["tax_regime"].normalized_value == "real_normal"
    assert fields["taxable_profit"].normalized_value == Decimal("10000000")
    assert fields["computed_corporate_tax"].normalized_value == Decimal("2750000")
    assert fields["corporate_tax_due"].normalized_value == Decimal("2750000")
    assert fields["minimum_tax_declared"].status is ResolutionStatus.UNRESOLVED


def test_extracts_is_from_excel_and_normalizes_simplified_regime(
    tmp_path: Path,
) -> None:
    source = tmp_path / "is.xlsx"
    pd.DataFrame(
        {
            "N IFU": ["9876543210"],
            "Designation de la societe": ["Petite Societe"],
            "Regime d imposition": ["Regime du Reel Simplifie"],
            "Resultat imposable": ["500 000"],
            "Chiffre d affaires HT": ["20 099 999"],
            "Impot calcule": ["137 500"],
            "Minimum forfaitaire": ["300 000"],
            "Situation IMFPIC": ["Droit commun"],
        },
    ).to_excel(source, index=False)
    reference = _reference(source, DeclarationSourceFormat.EXCEL)

    declaration = CorporateIncomeTaxTabularExtractor().extract(source, reference)

    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["tax_regime"].normalized_value == "real_simplified"
    assert fields["taxable_profit"].normalized_value == Decimal("500000")
    assert fields["annual_turnover_excluding_tax"].normalized_value == Decimal(
        "20099999",
    )
    assert fields["minimum_tax_declared"].normalized_value == Decimal("300000")
    assert fields["minimum_tax_treatment"].normalized_value == "standard"


def test_accepts_nif_without_assuming_ifu_shape(tmp_path: Path) -> None:
    source = tmp_path / "is-nif.csv"
    source.write_text(
        "NIF;Raison sociale;Regime;Benefice imposable;IS calcule;IS a payer\n"
        "00-AZ-19;Societe Test;Reel Normal;10000000;2750000;2750000\n",
        encoding="utf-8",
    )

    declaration = CorporateIncomeTaxTabularExtractor().extract(
        source,
        _reference(source, DeclarationSourceFormat.CSV),
    )

    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["company_identifier"].normalized_value == "00-AZ-19"
    assert fields["company_identifier_type"].normalized_value == "NIF"


def test_candidate_requires_regime_profit_and_computed_tax(tmp_path: Path) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text(
        "Raison sociale;Benefice imposable;IS calcule\n"
        "Societe Test;10000000;2750000\n",
        encoding="utf-8",
    )

    assert not CorporateIncomeTaxTabularExtractor().is_candidate(
        source,
        _reference(source, DeclarationSourceFormat.CSV),
    )


def _reference(
    source: Path,
    source_format: DeclarationSourceFormat,
) -> SourceReference:
    return SourceReference(
        file_name=source.name,
        source_format=source_format,
        content_type=None,
        content_sha256="a" * 64,
    )
