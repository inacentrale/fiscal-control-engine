from pathlib import Path

import pytest

from app.tax_declaration.domain import (
    DeclarationSourceFormat,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.payroll_tax_tabular_extractor import (
    PayrollTaxTabularExtractionError,
)
from app.tax_declaration.payroll_tax_xml_extractor import PayrollTaxXmlExtractor


def test_extracts_namespaced_iuts_xml(tmp_path: Path) -> None:
    source = tmp_path / "iuts.xml"
    source.write_text(
        "<Declaration xmlns='urn:tax'><Ligne><N_ordre>01</N_ordre>"
        "<Nom_du_salarie>Salarie Test</Nom_du_salarie>"
        "<Salaire_brut>350000</Salaire_brut>"
        "<Base_imposable>280000</Base_imposable>"
        "<Nombre_de_charges>2</Nombre_de_charges><IUTS>42237</IUTS>"
        "</Ligne></Declaration>",
        encoding="utf-8",
    )

    declaration = PayrollTaxXmlExtractor().extract(source, _reference(source))

    assert declaration.declaration_type is TaxDeclarationType.PAYROLL_TAX
    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["taxable_base"].normalized_value == 280000
    assert fields["dependent_count"].normalized_value == 2
    assert fields["iuts_amount"].normalized_value == 42237


def test_rejects_iuts_xml_entities(tmp_path: Path) -> None:
    source = tmp_path / "iuts.xml"
    source.write_text(
        "<!DOCTYPE x [<!ENTITY x 'unsafe'>]><x><IUTS>&x;</IUTS>"
        "<Base_imposable>1</Base_imposable></x>",
        encoding="utf-8",
    )

    with pytest.raises(PayrollTaxTabularExtractionError, match="unsafe"):
        PayrollTaxXmlExtractor().extract(source, _reference(source))


def _reference(source: Path) -> SourceReference:
    return SourceReference(
        file_name=source.name,
        source_format=DeclarationSourceFormat.XML,
        content_type="application/xml",
        content_sha256="a" * 64,
    )
