import csv
from datetime import date
from pathlib import Path

from app.ras_audit.account_mapping import (
    RasLedgerAccountRole,
    best_account_mapping,
    load_ras_ledger_account_mappings,
)

ROOT = Path(__file__).resolve().parents[4]


def test_organization_mapping_covers_every_unambiguous_gl_ras_account() -> None:
    mappings = load_ras_ledger_account_mappings(
        ROOT / "docs/reference/ras-ledger-account-mapping.organization.csv"
    )

    assert {mapping.account_pattern for mapping in mappings} == {
        "51201000",
        "61312000",
        "61361600",
        "61365000",
        "44531001",
        "44531002",
        "44585100",
    }
    assert all(mapping.match_type.value == "exact" for mapping in mappings)


def test_organization_mapping_does_not_promote_ambiguous_or_non_ras_accounts() -> None:
    mappings = load_ras_ledger_account_mappings(
        ROOT / "docs/reference/ras-ledger-account-mapping.organization.csv"
    )

    for account in (
        "34552001",
        "41100500",
        "44380002",
        "51200500",
        "60610000",
        "706000",
    ):
        assert (
            best_account_mapping(
                mappings,
                account,
                role=RasLedgerAccountRole.EXPENSE_CANDIDATE,
                posting_date=date(2026, 1, 1),
                company_code=None,
            )
            is None
        )
        assert (
            best_account_mapping(
                mappings,
                account,
                role=RasLedgerAccountRole.RAS_PAYABLE,
                posting_date=date(2026, 1, 1),
                company_code=None,
            )
            is None
        )


def test_organization_mapping_normal_sides_match_observed_gl_movements() -> None:
    mappings = load_ras_ledger_account_mappings(
        ROOT / "docs/reference/ras-ledger-account-mapping.organization.csv"
    )
    evidence_path = (
        ROOT / "docs/reference/ras-ledger-account-observed-sides.organization.csv"
    )
    with evidence_path.open(encoding="utf-8", newline="") as source:
        evidence = {row["account_number"]: row for row in csv.DictReader(source)}

    for mapping in mappings:
        row = evidence[mapping.account_pattern]
        expected_count = int(row[f"{mapping.normal_side.value}_line_count"])
        opposite_side = "credit" if mapping.normal_side.value == "debit" else "debit"
        opposite_count = int(row[f"{opposite_side}_line_count"])
        assert expected_count > 0
        assert opposite_count == 0
