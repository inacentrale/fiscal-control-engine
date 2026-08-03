from decimal import Decimal
from pathlib import Path

import pytest

from app.tax_declaration.corporate_income_tax_tabular_extractor import (
    CorporateIncomeTaxTabularExtractionError,
)
from app.tax_declaration.corporate_income_tax_xml_extractor import (
    CorporateIncomeTaxXmlExtractor,
)
from app.tax_declaration.domain import (
    DeclarationSourceFormat,
    SourceReference,
    TaxDeclarationType,
)


def test_extracts_namespaced_is_xml(tmp_path: Path) -> None:
    source = tmp_path / "is.xml"
    source.write_text(
        "<Declaration xmlns='urn:tax'><Ligne><IFU>0123456789</IFU>"
        "<Regime>Reel Normal</Regime>"
        "<Benefice_imposable>10000000</Benefice_imposable>"
        "<IS_calcule>2750000</IS_calcule></Ligne></Declaration>",
        encoding="utf-8",
    )

    declaration = CorporateIncomeTaxXmlExtractor().extract(
        source,
        _reference(source),
    )

    assert declaration.declaration_type is TaxDeclarationType.CORPORATE_INCOME_TAX
    fields = {field.name: field for field in declaration.records[0].fields}
    assert fields["tax_regime"].normalized_value == "real_normal"
    assert fields["taxable_profit"].normalized_value == Decimal("10000000")
    assert fields["computed_corporate_tax"].normalized_value == Decimal("2750000")


def test_rejects_is_xml_entities(tmp_path: Path) -> None:
    source = tmp_path / "is.xml"
    source.write_text(
        "<!DOCTYPE x [<!ENTITY x 'unsafe'>]><x><IS_calcule>&x;</IS_calcule>"
        "<Benefice_imposable>1</Benefice_imposable></x>",
        encoding="utf-8",
    )

    with pytest.raises(CorporateIncomeTaxTabularExtractionError, match="unsafe"):
        CorporateIncomeTaxXmlExtractor().extract(source, _reference(source))


def _reference(source: Path) -> SourceReference:
    return SourceReference(
        file_name=source.name,
        source_format=DeclarationSourceFormat.XML,
        content_type="application/xml",
        content_sha256="a" * 64,
    )
