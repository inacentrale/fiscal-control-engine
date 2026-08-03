import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

from app.rag_source.domain import RagSourceType

REQUIRED_COLUMNS = {
    "source_id",
    "declaration_scope",
    "source_kind",
    "official_url",
    "publication_or_version",
    "applicable_from",
    "applicable_to",
    "use_status",
    "corpus_status",
    "conflict_or_gap",
}


class TaxSourceUseStatus(StrEnum):
    ACTIVE_RULE_SOURCE = "active_rule_source"
    ACTIVE_STRUCTURE_SOURCE = "active_structure_source"
    REVIEW_REQUIRED = "review_required"
    FETCH_REQUIRED = "fetch_required"
    CONFLICT_REVIEW = "conflict_review"
    CANDIDATE_FUTURE_RULE = "candidate_future_rule"
    CONTEXT_ONLY = "context_only"


class TaxSourceCorpusStatus(StrEnum):
    INDEXED = "indexed"
    NOT_INDEXED = "not_indexed"
    EXCERPT_PENDING = "excerpt_pending"


@dataclass(frozen=True)
class TaxSourceInventoryEntry:
    source_id: str
    declaration_scope: tuple[str, ...]
    source_kind: RagSourceType
    official_url: str
    publication_or_version: str
    applicable_from: date | None
    applicable_to: date | None
    use_status: TaxSourceUseStatus
    corpus_status: TaxSourceCorpusStatus
    conflict_or_gap: str

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.declaration_scope:
            raise ValueError("declaration_scope is required")
        if not self.official_url.startswith("https://"):
            raise ValueError("official_url must use HTTPS")
        if not self.publication_or_version.strip():
            raise ValueError("publication_or_version is required")
        if (
            self.applicable_from is not None
            and self.applicable_to is not None
            and self.applicable_to < self.applicable_from
        ):
            raise ValueError("applicable_to must not precede applicable_from")


def load_tax_source_inventory(
    source_path: Path,
) -> tuple[TaxSourceInventoryEntry, ...]:
    with source_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames)
        entries = tuple(_build_entry(row) for row in reader if row)

    source_ids = [entry.source_id for entry in entries]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source_id values must be unique")
    return entries


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    missing_columns = REQUIRED_COLUMNS - set(fieldnames or ())
    if missing_columns:
        raise ValueError(
            f"missing inventory columns: {', '.join(sorted(missing_columns))}",
        )


def _build_entry(row: dict[str, str]) -> TaxSourceInventoryEntry:
    return TaxSourceInventoryEntry(
        source_id=row["source_id"].strip(),
        declaration_scope=tuple(
            scope.strip()
            for scope in row["declaration_scope"].split("|")
            if scope.strip()
        ),
        source_kind=RagSourceType(row["source_kind"].strip()),
        official_url=row["official_url"].strip(),
        publication_or_version=row["publication_or_version"].strip(),
        applicable_from=_parse_optional_date(row["applicable_from"]),
        applicable_to=_parse_optional_date(row["applicable_to"]),
        use_status=TaxSourceUseStatus(row["use_status"].strip()),
        corpus_status=TaxSourceCorpusStatus(row["corpus_status"].strip()),
        conflict_or_gap=row["conflict_or_gap"].strip(),
    )


def _parse_optional_date(value: str) -> date | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("applicability dates must use YYYY-MM-DD") from exc
