from pathlib import Path

from app.tax_declaration.domain import ResolutionStatus, TaxDeclarationType
from app.tax_declaration.ingestion_service import TaxDeclarationIngestionService


def test_auto_detects_and_ingests_vat_csv(tmp_path: Path) -> None:
    source = tmp_path / "unknown.upload"
    source.write_text(
        "Code;Nature;Montant\n15;Operations taxables;180000\n",
        encoding="utf-8",
    )

    result = TaxDeclarationIngestionService().ingest(source)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.declaration_type is TaxDeclarationType.VAT
    assert result.declaration is not None
    assert len(result.declaration.records) == 1


def test_auto_detects_and_ingests_iuts_csv(tmp_path: Path) -> None:
    source = tmp_path / "unknown.upload"
    source.write_text(
        "N ordre;Noms et prenoms des salaries;Salaires bruts;"
        "Bases imposables;Nombre de charge;IUTS du\n"
        "01;Salarie Test;350000;280000;2;42335\n",
        encoding="utf-8",
    )

    result = TaxDeclarationIngestionService().ingest(source)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.declaration_type is TaxDeclarationType.PAYROLL_TAX
    assert result.declaration is not None
    assert result.declaration.records[0].record_type == "payroll_tax_line"


def test_ingests_namespaced_vat_xml(tmp_path: Path) -> None:
    source = tmp_path / "declaration.data"
    source.write_text(
        "<Declaration xmlns='urn:tax'>"
        "<Ligne><Code>19</Code><Nature>Total TVA brute</Nature>"
        "<Montant>180000</Montant></Ligne>"
        "</Declaration>",
        encoding="utf-8",
    )

    result = TaxDeclarationIngestionService().ingest(source)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.declaration is not None
    assert result.declaration.records[0].record_type == "vat_line"


def test_auto_detects_and_ingests_withholding_xml(tmp_path: Path) -> None:
    source = tmp_path / "declaration.xml"
    source.write_text(
        "<Declaration><Ligne><Code>01</Code>"
        "<Regime_retenue>resident</Regime_retenue>"
        "<Categorie_taux>registered_standard</Categorie_taux>"
        "<Base>1000000</Base><Taux>5</Taux>"
        "<Montant_des_retenues>50000</Montant_des_retenues>"
        "</Ligne></Declaration>",
        encoding="utf-8",
    )

    result = TaxDeclarationIngestionService().ingest(source)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.declaration_type is TaxDeclarationType.WITHHOLDING_TAX
    assert result.declaration is not None
    assert result.declaration.records[0].record_type == "withholding_line"


def test_auto_detects_and_ingests_iuts_xml(tmp_path: Path) -> None:
    source = tmp_path / "declaration.xml"
    source.write_text(
        "<Declaration><Ligne><N_ordre>01</N_ordre>"
        "<Nom_du_salarie>Salarie Test</Nom_du_salarie>"
        "<Salaire_brut>350000</Salaire_brut>"
        "<Base_imposable>280000</Base_imposable>"
        "<Nombre_de_charges>2</Nombre_de_charges><IUTS>42237</IUTS>"
        "</Ligne></Declaration>",
        encoding="utf-8",
    )

    result = TaxDeclarationIngestionService().ingest(source)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.declaration_type is TaxDeclarationType.PAYROLL_TAX
    assert result.declaration is not None
    assert result.declaration.records[0].record_type == "payroll_tax_line"


def test_does_not_guess_scanned_image_content(tmp_path: Path) -> None:
    source = tmp_path / "scan.upload"
    source.write_bytes(b"\x89PNG\r\n\x1a\ncontent")

    result = TaxDeclarationIngestionService().ingest(source)

    assert result.status is ResolutionStatus.UNRESOLVED
    assert result.declaration_type is TaxDeclarationType.UNRESOLVED
    assert result.reason == "structure_unresolved"


def test_rejects_unsafe_xml_without_parsing_entities(tmp_path: Path) -> None:
    source = tmp_path / "declaration.xml"
    source.write_text(
        "<!DOCTYPE x [<!ENTITY x 'unsafe'>]><x><Nature>&x;</Nature>"
        "<Montant>1</Montant></x>",
        encoding="utf-8",
    )

    result = TaxDeclarationIngestionService().ingest(source)

    assert result.status is ResolutionStatus.UNRESOLVED
    assert result.reason == "structure_unresolved"
