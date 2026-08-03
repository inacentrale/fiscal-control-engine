from pathlib import Path

from app.account_mapping.domain import ClassificationStatus
from app.account_mapping.import_service import AccountMappingImportService
from app.account_mapping.repository import InMemoryAccountMappingRepository
from app.account_mapping.rule_loader import load_classification_rules
from app.account_mapping.service import AccountMappingService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_representative_fixture_imports_expected_account_counts() -> None:
    import_service = AccountMappingImportService()

    ledger_accounts = import_service.read_ledger_accounts(
        FIXTURES_DIR / "ledger_accounts.csv",
    )
    plan_accounts = import_service.read_plan_accounts(
        FIXTURES_DIR / "plan_accounts.csv",
    )

    assert len(ledger_accounts) == 139
    assert len(plan_accounts) == 138
    assert {account.number for account in ledger_accounts} - {
        account.number for account in plan_accounts
    } == {"44910002"}


def test_representative_fixture_builds_mapping_with_missing_label_account() -> None:
    import_service = AccountMappingImportService()
    mapping_service = AccountMappingService(
        repository=InMemoryAccountMappingRepository(),
        rules=load_classification_rules(FIXTURES_DIR / "ras_classification_rules.csv"),
    )

    mappings = mapping_service.build_from_accounts(
        ledger_accounts=import_service.read_ledger_accounts(
            FIXTURES_DIR / "ledger_accounts.csv",
        ),
        plan_accounts=import_service.read_plan_accounts(
            FIXTURES_DIR / "plan_accounts.csv",
        ),
    )

    missing_label_mappings = [
        mapping
        for mapping in mappings
        if mapping.classification_status is ClassificationStatus.MISSING_LABEL
    ]

    assert len(mappings) == 139
    assert len(missing_label_mappings) == 1
    assert missing_label_mappings[0].account_number == "44910002"
