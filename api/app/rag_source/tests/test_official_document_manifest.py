from hashlib import sha256
from pathlib import Path

from app.rag_source.official_document_manifest import (
    DocumentStorageStatus,
    load_official_document_manifest,
)
from app.rag_source.tax_source_inventory import load_tax_source_inventory

_ROOT = Path(__file__).parents[4]
_MANIFEST = _ROOT / "docs" / "reference" / "bf-tax-official-document-manifest.csv"
_INVENTORY = _ROOT / "docs" / "reference" / "bf-tax-source-inventory.csv"


def test_manifest_is_valid_and_references_inventory_sources() -> None:
    entries = load_official_document_manifest(_MANIFEST)
    inventory_ids = {
        entry.source_id for entry in load_tax_source_inventory(_INVENTORY)
    }

    assert len(entries) == 6
    assert {entry.source_id for entry in entries}.issubset(inventory_ids)
    assert sum(
        entry.storage_status is DocumentStorageStatus.VERSIONED
        for entry in entries
    ) == 1


def test_versioned_cgi_matches_manifest_hash_and_size() -> None:
    entry = next(
        item
        for item in load_official_document_manifest(_MANIFEST)
        if item.source_id == "bf_cgi_consolidated_2023"
    )
    document = _ROOT / entry.local_path
    content = document.read_bytes()

    assert len(content) == entry.byte_size
    assert sha256(content).hexdigest() == entry.sha256
