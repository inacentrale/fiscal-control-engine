from app.tax_declaration.identifier_detection import (
    infer_identifier_kind,
    normalize_explicit_identifier_kind,
)


def test_infers_known_and_source_defined_identifier_kinds_from_labels() -> None:
    assert infer_identifier_kind("Numéro IFU") == "IFU"
    assert infer_identifier_kind("NIF") == "NIF"
    assert infer_identifier_kind("Tax Identification Number") == "TIN"
    assert (
        infer_identifier_kind("Identifiant partenaire ERP")
        == "IDENTIFIANT_PARTENAIRE_ERP"
    )


def test_does_not_infer_identifier_kind_from_unrelated_label() -> None:
    assert infer_identifier_kind("Montant") is None
    assert normalize_explicit_identifier_kind("Code fiscal interne") == (
        "CODE_FISCAL_INTERNE"
    )
