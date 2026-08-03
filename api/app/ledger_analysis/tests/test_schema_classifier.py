from app.excel_agent.domain import ExcelColumnProfile
from app.ledger_analysis.schema_classifier import LedgerSchemaClassifier


def test_classifier_maps_sap_like_columns_to_canonical_schema() -> None:
    classifier = LedgerSchemaClassifier()

    result = classifier.classify(
        (
            _column("Nº pièce", "number", 0),
            _column("Compte", "number", 1),
            _column("Type de pièce", "text", 2),
            _column("Période comptable", "number", 3),
            _column("Montant en devise interne", "number", 4),
            _column("Devise interne", "text", 5),
            _column("Code TVA", "text", 6),
            _column("Texte", "text", 7),
            _column("Client", "number", 8, missing_ratio=0.8),
            _column("Fournisseur", "number", 9, missing_ratio=0.5),
            _column("Exercice comptable", "number", 10),
            _column("Clé comptabilisation", "number", 11),
        ),
    )

    assert result.is_usable is True
    assert result.requires_confirmation is False
    assert result.get_mapping("account").source_column == "Compte"
    assert result.get_mapping("amount").source_column == "Montant en devise interne"
    assert result.get_mapping("currency").source_column == "Devise interne"
    assert result.get_mapping("text").source_column == "Texte"
    assert result.get_mapping("vendor").source_column == "Fournisseur"
    assert result.get_mapping("customer").source_column == "Client"
    assert result.get_mapping("tax_code").source_column == "Code TVA"
    assert result.get_mapping("period").source_column == "Période comptable"
    assert result.get_mapping("fiscal_year").source_column == "Exercice comptable"
    assert result.get_mapping("document_type").source_column == "Type de pièce"
    assert result.get_mapping("posting_key").source_column == "Clé comptabilisation"
    assert all(mapping.status == "mapped" for mapping in result.mappings)


def test_classifier_marks_low_confidence_or_ambiguous_columns_to_confirm() -> None:
    classifier = LedgerSchemaClassifier()

    result = classifier.classify(
        (
            _column("Montant 1", "number", 0),
            _column("Montant 2", "number", 1),
            _column("Description", "text", 2),
        ),
    )

    assert result.is_usable is False
    assert result.requires_confirmation is True
    assert result.get_mapping("amount").status == "a_confirmer"
    assert result.get_mapping("account").status == "missing"


def test_classifier_prefers_document_amount_and_currency() -> None:
    classifier = LedgerSchemaClassifier()

    result = classifier.classify(
        (
            _column("Compte", "number", 0),
            _column("Texte", "text", 1),
            _column("Montant devise document", "number", 2),
            _column("Devise pièce", "text", 3),
            _column("Montant en devise interne", "number", 4),
            _column("Devise interne", "text", 5),
        ),
    )

    assert result.get_mapping("amount").source_column == "Montant devise document"
    assert result.get_mapping("currency").source_column == "Devise pièce"


def test_classifier_does_not_expose_cell_values() -> None:
    classifier = LedgerSchemaClassifier()

    result = classifier.classify(
        (
            _column("Compte", "number", 0),
            _column("Texte", "text", 1),
        ),
    )

    serialized_result = repr(result)
    assert "Achat fournitures" not in serialized_result
    assert "601000" not in serialized_result


def _column(
    name: str,
    detected_type: str,
    position: int,
    missing_ratio: float = 0.0,
) -> ExcelColumnProfile:
    return ExcelColumnProfile(
        name=name,
        position=position,
        detected_type=detected_type,
        non_empty_count=100,
        missing_count=int(missing_ratio * 100),
        missing_ratio=missing_ratio,
    )
