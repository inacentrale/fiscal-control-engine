import csv
from dataclasses import dataclass
from pathlib import Path
from unicodedata import normalize

from app.ras_audit.domain import LedgerField
from app.ras_audit.normalization import LedgerColumnBinding


class LedgerColumnAliasError(ValueError):
    pass


@dataclass(frozen=True)
class LedgerColumnAlias:
    version: str
    field: LedgerField
    alias: str


@dataclass(frozen=True)
class LedgerColumnAmbiguity:
    field: LedgerField
    source_columns: tuple[str, ...]


@dataclass(frozen=True)
class LedgerColumnResolution:
    version: str
    bindings: tuple[LedgerColumnBinding, ...]
    missing_fields: tuple[LedgerField, ...]
    ambiguities: tuple[LedgerColumnAmbiguity, ...]

    @property
    def is_unambiguous(self) -> bool:
        return not self.ambiguities


def load_ledger_column_aliases(path: Path) -> tuple[LedgerColumnAlias, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            rows = tuple(csv.DictReader(source))
    except OSError as exc:
        raise LedgerColumnAliasError("ledger column aliases cannot be read") from exc

    aliases: list[LedgerColumnAlias] = []
    normalized_alias_fields: dict[str, LedgerField] = {}
    seen_pairs: set[tuple[LedgerField, str]] = set()
    versions: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        version = (row.get("version") or "").strip()
        raw_field = (row.get("field") or "").strip()
        alias = (row.get("alias") or "").strip()
        if not version or not raw_field or not alias:
            raise LedgerColumnAliasError(
                f"incomplete ledger column alias at row {row_number}"
            )
        try:
            field = LedgerField(raw_field)
        except ValueError as exc:
            raise LedgerColumnAliasError(
                f"unknown ledger field at row {row_number}"
            ) from exc
        normalized_alias = normalize_column_name(alias)
        pair = (field, normalized_alias)
        if pair in seen_pairs:
            raise LedgerColumnAliasError(
                f"duplicate ledger column alias at row {row_number}"
            )
        conflicting_field = normalized_alias_fields.get(normalized_alias)
        if conflicting_field is not None and conflicting_field is not field:
            raise LedgerColumnAliasError(
                f"ledger column alias maps to multiple fields at row {row_number}"
            )
        seen_pairs.add(pair)
        normalized_alias_fields[normalized_alias] = field
        versions.add(version)
        aliases.append(LedgerColumnAlias(version, field, alias))
    if len(versions) != 1:
        raise LedgerColumnAliasError("exactly one alias version is required")
    return tuple(aliases)


def resolve_ledger_columns(
    source_columns: tuple[str, ...],
    aliases: tuple[LedgerColumnAlias, ...],
) -> LedgerColumnResolution:
    if not aliases:
        raise LedgerColumnAliasError("ledger column aliases are empty")
    normalized_sources: dict[str, list[str]] = {}
    for source_column in source_columns:
        normalized_sources.setdefault(
            normalize_column_name(source_column),
            [],
        ).append(source_column)

    aliases_by_field: dict[LedgerField, set[str]] = {}
    for alias in aliases:
        aliases_by_field.setdefault(alias.field, set()).add(
            normalize_column_name(alias.alias)
        )

    bindings: list[LedgerColumnBinding] = []
    missing_fields: list[LedgerField] = []
    ambiguities: list[LedgerColumnAmbiguity] = []
    for field in LedgerField:
        matching_columns = tuple(
            source_column
            for normalized_alias in aliases_by_field.get(field, set())
            for source_column in normalized_sources.get(normalized_alias, ())
        )
        if not matching_columns:
            missing_fields.append(field)
        elif len(matching_columns) == 1:
            bindings.append(LedgerColumnBinding(field, matching_columns[0]))
        else:
            ambiguities.append(
                LedgerColumnAmbiguity(
                    field=field,
                    source_columns=tuple(sorted(matching_columns)),
                ),
            )
    bound_fields = {binding.field for binding in bindings}
    partner_fields = {
        LedgerField.PARTNER_ID,
        LedgerField.VENDOR_ID,
        LedgerField.CUSTOMER_ID,
    }
    missing_fields = [field for field in missing_fields if field not in partner_fields]
    if not (bound_fields & partner_fields):
        missing_fields.append(LedgerField.PARTNER_ID)
    return LedgerColumnResolution(
        version=aliases[0].version,
        bindings=tuple(bindings),
        missing_fields=tuple(missing_fields),
        ambiguities=tuple(ambiguities),
    )


def normalize_column_name(value: str) -> str:
    without_accents = normalize("NFKD", value)
    ascii_value = without_accents.encode("ascii", "ignore").decode("ascii")
    characters = (
        character.lower() if character.isalnum() else " "
        for character in ascii_value
    )
    return " ".join("".join(characters).split())
