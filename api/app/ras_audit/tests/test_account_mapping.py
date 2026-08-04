from datetime import date
from pathlib import Path

import pytest

from app.ras_audit.account_mapping import (
    RasLedgerAccountMappingError,
    RasLedgerAccountRole,
    best_account_mapping,
    has_applicable_ras_payable_mapping,
    has_ras_payable_mapping,
    load_ras_ledger_account_mappings,
    matching_account_mappings,
)


def test_loads_and_resolves_synthetic_organization_mapping() -> None:
    mappings = load_ras_ledger_account_mappings(_fixtures_path() / "valid.csv")

    assert len(mappings) == 5
    assert has_ras_payable_mapping(mappings) is True
    matches = matching_account_mappings(
        mappings,
        "447100",
        posting_date=date(2025, 3, 1),
        company_code="SYN-CO",
    )
    assert len(matches) == 1
    assert matches[0].role is RasLedgerAccountRole.RAS_PAYABLE
    assert best_account_mapping(
        mappings,
        "632100",
        role=RasLedgerAccountRole.EXPENSE_CANDIDATE,
        posting_date=date(2025, 3, 1),
        company_code="SYN-CO",
    ) is not None
    assert has_applicable_ras_payable_mapping(
        mappings,
        posting_date=date(2025, 3, 1),
        company_code="SYN-CO",
    ) is True
    assert has_applicable_ras_payable_mapping(
        mappings,
        posting_date=date(2025, 3, 1),
        company_code="OTHER",
    ) is False


def test_does_not_apply_mapping_outside_company_or_validity() -> None:
    mappings = load_ras_ledger_account_mappings(_fixtures_path() / "valid.csv")

    assert matching_account_mappings(
        mappings,
        "447200",
        posting_date=date(2025, 3, 1),
        company_code="SYN-CO",
    ) == ()
    assert matching_account_mappings(
        mappings,
        "447100",
        posting_date=date(2025, 3, 1),
        company_code="OTHER",
    ) == ()


def test_rejects_overlapping_organization_mappings() -> None:
    with pytest.raises(
        RasLedgerAccountMappingError,
        match="overlapping RAS ledger account mappings",
    ):
        load_ras_ledger_account_mappings(_fixtures_path() / "overlap.csv")


def test_empty_template_is_not_treated_as_available_mapping() -> None:
    template = (
        Path(__file__).parents[4]
        / "docs"
        / "reference"
        / "ras-ledger-account-mapping.template.csv"
    )

    with pytest.raises(RasLedgerAccountMappingError, match="mapping is empty"):
        load_ras_ledger_account_mappings(template)


def _fixtures_path() -> Path:
    return Path(__file__).parent / "fixtures" / "account-mapping"
