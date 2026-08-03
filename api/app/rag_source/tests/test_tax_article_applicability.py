from datetime import date
from pathlib import Path

from app.rag_source.tax_article_applicability import (
    ArticleVerificationStatus,
    load_tax_article_applicability,
)
from app.rag_source.tax_source_inventory import load_tax_source_inventory

_ROOT = Path(__file__).parents[4]
_MATRIX = _ROOT / "docs" / "reference" / "bf-tax-article-applicability-matrix.csv"
_INVENTORY = _ROOT / "docs" / "reference" / "bf-tax-source-inventory.csv"


def test_matrix_is_valid_and_references_inventory() -> None:
    entries = load_tax_article_applicability(_MATRIX)
    inventory_ids = {
        item.source_id for item in load_tax_source_inventory(_INVENTORY)
    }

    assert len(entries) == 38
    assert {item.legal_source_id for item in entries}.issubset(inventory_ids)
    assert {item.tax_scope for item in entries} == {"TVA", "RAS", "IUTS", "IS"}


def test_each_controlled_article_has_coverage_from_2023_through_2026() -> None:
    entries = load_tax_article_applicability(_MATRIX)
    expected = {
        "TVA": {"317", "334"},
        "RAS": {"207", "208", "212", "214", "221", "222"},
        "IUTS": {"112", "113", "116"},
        "IS": {"87", "89", "90", "91", "92", "95"},
    }
    for tax_scope, articles in expected.items():
        for article in articles:
            rows = tuple(
                item
                for item in entries
                if item.tax_scope == tax_scope and item.cgi_article == article
            )
            for year in range(2023, 2027):
                point = date(year, 7, 1)
                assert sum(
                    row.valid_from <= point <= row.valid_to for row in rows
                ) == 1


def test_matrix_exposes_unverified_periods_instead_of_assuming_no_change() -> None:
    entries = load_tax_article_applicability(_MATRIX)

    assert any(
        item.verification_status is ArticleVerificationStatus.REVIEW_REQUIRED
        and item.valid_from.year == 2024
        for item in entries
    )
    assert all(
        item.gap_reason
        for item in entries
        if item.verification_status is not ArticleVerificationStatus.CONFIRMED
    )
