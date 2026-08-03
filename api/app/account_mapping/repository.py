from abc import ABC, abstractmethod

from app.account_mapping.domain import AccountMapping


class AccountMappingRepository(ABC):
    @abstractmethod
    def save_all(self, mappings: list[AccountMapping]) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[AccountMapping]:
        raise NotImplementedError


class InMemoryAccountMappingRepository(AccountMappingRepository):
    def __init__(self) -> None:
        self._mappings_by_account_number: dict[str, AccountMapping] = {}

    def save_all(self, mappings: list[AccountMapping]) -> None:
        for mapping in mappings:
            self._mappings_by_account_number[mapping.account_number] = mapping

    def list_all(self) -> list[AccountMapping]:
        return [
            self._mappings_by_account_number[account_number]
            for account_number in sorted(self._mappings_by_account_number)
        ]
