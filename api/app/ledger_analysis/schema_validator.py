from dataclasses import dataclass
from unicodedata import normalize

from app.ledger_analysis.constants import REQUIRED_LEDGER_COLUMNS


class LedgerSchemaValidationError(ValueError):
    pass


@dataclass(frozen=True)
class LedgerSchemaReport:
    is_valid: bool
    present_columns: tuple[str, ...]
    missing_required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]


class LedgerSchemaValidator:
    def __init__(
        self,
        required_columns: tuple[str, ...] = REQUIRED_LEDGER_COLUMNS,
        optional_columns: tuple[str, ...] = (),
    ) -> None:
        self._required_columns = required_columns
        self._optional_columns = optional_columns

    def validate(self, columns: tuple[str, ...]) -> LedgerSchemaReport:
        normalized_to_original = {
            _normalize_column_name(column): column for column in columns
        }
        missing_required_columns = tuple(
            required_column
            for required_column in self._required_columns
            if _normalize_column_name(required_column) not in normalized_to_original
        )
        optional_columns = tuple(
            normalized_to_original[_normalize_column_name(optional_column)]
            for optional_column in self._optional_columns
            if _normalize_column_name(optional_column) in normalized_to_original
        )
        return LedgerSchemaReport(
            is_valid=not missing_required_columns,
            present_columns=tuple(columns),
            missing_required_columns=missing_required_columns,
            optional_columns=optional_columns,
        )


def _normalize_column_name(column_name: str) -> str:
    without_accents = normalize("NFKD", column_name)
    ascii_name = without_accents.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_name.lower().split())
