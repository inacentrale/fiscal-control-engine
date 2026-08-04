from pathlib import Path

from app.ras_audit.column_aliases import (
    load_ledger_column_aliases,
    resolve_ledger_columns,
)
from app.ras_audit.domain import LedgerField


def test_resolves_supported_french_gl_columns_without_guessing() -> None:
    aliases = load_ledger_column_aliases(_reference_path())

    resolution = resolve_ledger_columns(
        (
            "Société",
            "Exercice",
            "Période",
            "Journal",
            "Numéro pièce",
            "Numéro ligne",
            "Date comptable",
            "Compte général",
            "Tiers",
            "Libellé",
            "Clé de comptabilisation",
            "Montant devise document",
            "Devise du document",
        ),
        aliases,
    )

    assert resolution.version == "bf.ras-gl-columns.v2"
    assert resolution.is_unambiguous is True
    assert resolution.missing_fields == ()
    assert len(resolution.bindings) == len(LedgerField) - 2


def test_resolves_vendor_and_customer_as_distinct_partner_sources() -> None:
    resolution = resolve_ledger_columns(
        ("Compte", "Fournisseur", "Client", "Libelle"),
        load_ledger_column_aliases(_reference_path()),
    )

    assert resolution.is_unambiguous is True
    bindings = {binding.field: binding.source_column for binding in resolution.bindings}
    assert bindings[LedgerField.VENDOR_ID] == "Fournisseur"
    assert bindings[LedgerField.CUSTOMER_ID] == "Client"
    assert LedgerField.PARTNER_ID not in bindings


def _reference_path() -> Path:
    return (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "ras-gl-column-aliases.csv"
    )
