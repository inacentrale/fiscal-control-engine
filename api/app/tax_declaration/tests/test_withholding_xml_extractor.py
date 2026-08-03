from pathlib import Path

import pytest

from app.tax_declaration.domain import (
    DeclarationSourceFormat,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.withholding_tabular_extractor import (
    WithholdingTabularExtractionError,
)
from app.tax_declaration.withholding_xml_extractor import WithholdingXmlExtractor


def test_extracts_namespaced_withholding_xml(tmp_path: Path) -> None:
    source = tmp_path / "ras.xml"
    source.write_text(
        "<Declaration xmlns='urn:tax'><Ligne>"
        "<Code>01</Code><Regime_retenue>resident</Regime_retenue>"
        "<Categorie_taux>registered_standard</Categorie_taux>"
        "<Base>1000000</Base><Taux>5</Taux>"
        "<Montant_des_retenues>50000</Montant_des_retenues>"
        "</Ligne></Declaration>",
        encoding="utf-8",
    )

    declaration = WithholdingXmlExtractor().extract(source, _reference(source))

    assert declaration.declaration_type is TaxDeclarationType.WITHHOLDING_TAX
    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["line_code"].normalized_value == "01"
    assert fields["tax_base"].normalized_value == 1000000
    assert fields["withheld_amount"].normalized_value == 50000


def test_rejects_xml_entities(tmp_path: Path) -> None:
    source = tmp_path / "ras.xml"
    source.write_text(
        "<!DOCTYPE x [<!ENTITY x 'unsafe'>]><x><Categorie>&x;</Categorie>"
        "<Montant_des_retenues>1</Montant_des_retenues></x>",
        encoding="utf-8",
    )

    with pytest.raises(WithholdingTabularExtractionError, match="unsafe"):
        WithholdingXmlExtractor().extract(source, _reference(source))


def _reference(source: Path) -> SourceReference:
    return SourceReference(
        file_name=source.name,
        source_format=DeclarationSourceFormat.XML,
        content_type="application/xml",
        content_sha256="a" * 64,
    )
