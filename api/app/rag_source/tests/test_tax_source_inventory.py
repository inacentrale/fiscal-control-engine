from pathlib import Path

import pytest

from app.rag_source.domain import RagSourceType
from app.rag_source.tax_source_inventory import (
    TaxSourceCorpusStatus,
    TaxSourceUseStatus,
    load_tax_source_inventory,
)

_INVENTORY_PATH = (
    Path(__file__).parents[4] / "docs" / "reference" / "bf-tax-source-inventory.csv"
)


def test_official_tax_source_inventory_is_valid_and_unique() -> None:
    entries = load_tax_source_inventory(_INVENTORY_PATH)

    assert len(entries) == 15
    assert len({entry.source_id for entry in entries}) == 15
    assert all(entry.official_url.startswith("https://") for entry in entries)


def test_inventory_distinguishes_indexed_sources_and_conflicts() -> None:
    entries = load_tax_source_inventory(_INVENTORY_PATH)
    by_id = {entry.source_id: entry for entry in entries}

    vat_form = by_id["bf_vat_form_2023_10"]
    assert vat_form.source_kind is RagSourceType.OFFICIAL_FORM
    assert vat_form.use_status is TaxSourceUseStatus.ACTIVE_STRUCTURE_SOURCE
    assert vat_form.corpus_status is TaxSourceCorpusStatus.INDEXED

    installments = by_id["bf_is_installments_form_2023_10"]
    assert installments.use_status is TaxSourceUseStatus.ACTIVE_STRUCTURE_SOURCE
    assert installments.corpus_status is TaxSourceCorpusStatus.INDEXED
    assert "20" in installments.conflict_or_gap
    assert "15" in installments.conflict_or_gap

    domicile = by_id["bf_iuts_domicile_instruction"]
    assert domicile.use_status is TaxSourceUseStatus.CONTEXT_ONLY
    assert domicile.corpus_status is TaxSourceCorpusStatus.INDEXED

    law_2023 = by_id["bf_finance_law_2023"]
    assert law_2023.use_status is TaxSourceUseStatus.REVIEW_REQUIRED
    assert law_2023.corpus_status is TaxSourceCorpusStatus.EXCERPT_PENDING

    rectifying_2025 = by_id["bf_finance_rectifying_law_2025"]
    assert rectifying_2025.use_status is TaxSourceUseStatus.FETCH_REQUIRED
    assert rectifying_2025.corpus_status is TaxSourceCorpusStatus.NOT_INDEXED


def test_inventory_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    source_path = tmp_path / "inventory.csv"
    header = (
        "source_id,declaration_scope,source_kind,official_url,"
        "publication_or_version,applicable_from,applicable_to,use_status,"
        "corpus_status,conflict_or_gap\n"
    )
    row = (
        "duplicate,TVA,official_form,https://dgi.bf/form.pdf,2026,"
        "2026-01-01,,active_structure_source,indexed,\n"
    )
    source_path.write_text(header + row + row, encoding="utf-8")

    with pytest.raises(ValueError, match="source_id values must be unique"):
        load_tax_source_inventory(source_path)
