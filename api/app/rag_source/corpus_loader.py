import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.rag_source.domain import (
    RagSourceMetadata,
    RagSourceOrigin,
    RagSourceType,
    RagTextBlock,
    RagTextBlockType,
)

REQUIRED_CORPUS_COLUMNS = {
    "source_id",
    "source_type",
    "title",
    "version",
    "block_reference",
    "block_type",
    "theme",
    "text",
}


@dataclass(frozen=True)
class RagCorpusBlock:
    metadata: RagSourceMetadata
    block: RagTextBlock


def load_rag_corpus_blocks(source_path: Path) -> tuple[RagCorpusBlock, ...]:
    with source_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _validate_columns(reader.fieldnames)
        return tuple(_build_corpus_block(row, source_path) for row in reader if row)


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    columns = set(fieldnames or [])
    missing_columns = REQUIRED_CORPUS_COLUMNS - columns
    if missing_columns:
        raise ValueError(
            f"missing corpus columns: {', '.join(sorted(missing_columns))}",
        )


def _build_corpus_block(row: dict[str, str], source_path: Path) -> RagCorpusBlock:
    theme = row["theme"].strip()
    metadata = RagSourceMetadata(
        domain=_infer_domain(row["source_type"]),
        source_type=RagSourceType(row["source_type"].strip()),
        title=row["title"],
        version=row["version"],
        language="fr",
        origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
        source_path=str(source_path),
        themes=(theme,),
    )
    block = RagTextBlock(
        block_type=RagTextBlockType(row["block_type"].strip()),
        reference=row["block_reference"],
        heading=theme,
        text=row["text"],
    )
    return RagCorpusBlock(metadata=metadata, block=block)


def _infer_domain(source_type: str) -> str:
    if source_type.strip() in {"tax_code", "doctrine", "rate_reference"}:
        return "fiscal"
    return "compliance"
