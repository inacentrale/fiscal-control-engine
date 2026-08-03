from pathlib import Path

import pandas as pd

from app.tax_declaration.domain import (
    DeclarationSourceFormat,
    ResolutionStatus,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.payroll_tax_schema import (
    BURKINA_FASO_PAYROLL_TAX_SCHEMA,
    PAYROLL_TAX_OFFICIAL_FORM_URL,
)
from app.tax_declaration.payroll_tax_tabular_extractor import (
    PayrollTaxTabularExtractor,
)


def test_schema_is_sourced_from_official_dgi_form() -> None:
    schema = BURKINA_FASO_PAYROLL_TAX_SCHEMA

    assert schema.version == "bf.iuts.v1"
    assert schema.declaration_type is TaxDeclarationType.PAYROLL_TAX
    assert schema.official_source_urls == (PAYROLL_TAX_OFFICIAL_FORM_URL,)
    assert PAYROLL_TAX_OFFICIAL_FORM_URL.startswith("https://dgi.bf/")
    assert schema.record_fields == (
        "line_number",
        "employee_identifier",
        "employee_name",
        "gross_salary",
        "taxable_base",
        "dependent_count",
        "iuts_amount",
    )


def test_extracts_official_iuts_columns_from_csv(tmp_path: Path) -> None:
    source = tmp_path / "iuts.csv"
    source.write_text(
        "N ordre;Noms et prenoms des salaries;Salaires bruts;"
        "Bases imposables;Nombre de charge;IUTS du\n"
        "01;Salarie Test;350000;280000;2;42237\n",
        encoding="utf-8",
    )
    reference = _reference(source, DeclarationSourceFormat.CSV)

    declaration = PayrollTaxTabularExtractor().extract(source, reference)

    assert declaration.declaration_type is TaxDeclarationType.PAYROLL_TAX
    assert declaration.schema_version == "bf.iuts.v1"
    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["line_number"].normalized_value == "01"
    assert fields["employee_name"].normalized_value == "Salarie Test"
    assert fields["gross_salary"].normalized_value == 350000
    assert fields["taxable_base"].normalized_value == 280000
    assert fields["dependent_count"].normalized_value == 2
    assert fields["iuts_amount"].normalized_value == 42237
    assert all(field.status is ResolutionStatus.RESOLVED for field in fields.values())


def test_extracts_iuts_from_excel_and_preserves_identifiers(tmp_path: Path) -> None:
    source = tmp_path / "iuts.xlsx"
    pd.DataFrame(
        {
            "Numero": ["001"],
            "Matricule salarie": ["EMP-001"],
            "Nom du salarie": ["Salarie Test"],
            "Salaire brut": ["350 000"],
            "Base imposable": ["280 000"],
            "Nombre de charges": [2],
            "Montant IUTS": ["42 335"],
        },
    ).to_excel(source, index=False)
    reference = _reference(source, DeclarationSourceFormat.EXCEL)

    declaration = PayrollTaxTabularExtractor().extract(source, reference)

    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["line_number"].normalized_value == "001"
    assert fields["employee_identifier"].normalized_value == "EMP-001"
    assert fields["iuts_amount"].normalized_value == 42335


def test_candidate_requires_all_three_iuts_amount_columns(tmp_path: Path) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text(
        "Nom du salarie;Salaire brut;IUTS\nSalarie Test;350000;42335\n",
        encoding="utf-8",
    )

    assert not PayrollTaxTabularExtractor().is_candidate(
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
