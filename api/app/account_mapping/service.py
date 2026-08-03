from app.account_mapping.classifier import AccountMappingClassifier, ClassificationRule
from app.account_mapping.domain import (
    AccountMapping,
    GeneralLedgerAccount,
    PlanAccount,
)
from app.account_mapping.repository import AccountMappingRepository


class AccountMappingService:
    def __init__(
        self,
        repository: AccountMappingRepository,
        rules: tuple[ClassificationRule, ...],
    ) -> None:
        self._repository = repository
        self._classifier = AccountMappingClassifier(rules=rules)

    def build_from_accounts(
        self,
        ledger_accounts: list[GeneralLedgerAccount],
        plan_accounts: list[PlanAccount],
    ) -> list[AccountMapping]:
        plan_labels = {account.number: account.label for account in plan_accounts}
        unique_ledger_accounts = _deduplicate_ledger_accounts(ledger_accounts)
        mappings = [
            self._classifier.classify(
                ledger_account=ledger_account,
                label=plan_labels.get(ledger_account.number, ""),
            )
            for ledger_account in unique_ledger_accounts
        ]

        self._repository.save_all(mappings)
        return mappings


def _deduplicate_ledger_accounts(
    ledger_accounts: list[GeneralLedgerAccount],
) -> list[GeneralLedgerAccount]:
    accounts_by_number: dict[str, GeneralLedgerAccount] = {}
    for account in ledger_accounts:
        if account.number not in accounts_by_number:
            accounts_by_number[account.number] = account
    return list(accounts_by_number.values())
