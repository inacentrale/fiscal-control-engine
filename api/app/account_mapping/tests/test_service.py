from pathlib import Path

from app.account_mapping.domain import (
    ClassificationStatus,
    GeneralLedgerAccount,
    PlanAccount,
    RasCategory,
)
from app.account_mapping.repository import InMemoryAccountMappingRepository
from app.account_mapping.rule_loader import load_classification_rules
from app.account_mapping.service import AccountMappingService

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def build_service(
    repository: InMemoryAccountMappingRepository,
) -> AccountMappingService:
    return AccountMappingService(
        repository=repository,
        rules=load_classification_rules(FIXTURES_DIR / "ras_classification_rules.csv"),
    )


def test_service_maps_ledger_accounts_with_plan_labels() -> None:
    repository = InMemoryAccountMappingRepository()
    service = build_service(repository)

    result = service.build_from_accounts(
        ledger_accounts=[
            GeneralLedgerAccount(number="62210000"),
            GeneralLedgerAccount(number="44910002"),
        ],
        plan_accounts=[
            PlanAccount(number="62210000", label="HONORAIRES"),
        ],
    )

    assert len(result) == 2
    assert result[0].label == "HONORAIRES"
    assert result[0].classification_status is ClassificationStatus.CLASSIFIED
    assert result[0].ras_category is RasCategory.RESIDENT_SERVICES
    assert result[1].account_number == "44910002"
    assert result[1].classification_status is ClassificationStatus.MISSING_LABEL
    assert {mapping.account_number for mapping in repository.list_all()} == {
        mapping.account_number for mapping in result
    }


def test_service_deduplicates_ledger_accounts_preserving_first_order() -> None:
    service = build_service(InMemoryAccountMappingRepository())

    result = service.build_from_accounts(
        ledger_accounts=[
            GeneralLedgerAccount(number="62210000"),
            GeneralLedgerAccount(number="62210000"),
            GeneralLedgerAccount(number="61320000"),
        ],
        plan_accounts=[
            PlanAccount(number="62210000", label="HONORAIRES"),
            PlanAccount(number="61320000", label="LOYERS"),
        ],
    )

    assert [mapping.account_number for mapping in result] == ["62210000", "61320000"]


def test_service_uses_last_plan_label_for_duplicate_plan_accounts() -> None:
    service = build_service(InMemoryAccountMappingRepository())

    result = service.build_from_accounts(
        ledger_accounts=[GeneralLedgerAccount(number="62210000")],
        plan_accounts=[
            PlanAccount(number="62210000", label="ANCIEN LIBELLE"),
            PlanAccount(number="62210000", label="HONORAIRES"),
        ],
    )

    assert result[0].label == "HONORAIRES"
