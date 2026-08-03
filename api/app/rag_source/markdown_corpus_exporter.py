import csv
from dataclasses import dataclass
from pathlib import Path

from app.rag_source.corpus_loader import RagCorpusBlock
from app.rag_source.markdown_source_loader import load_markdown_source_blocks
from app.rag_source.source_corpus_validator import (
    find_source_corpus_files,
    validate_source_corpus_file,
)

CORPUS_EXPORT_COLUMNS = (
    "source_id",
    "source_type",
    "title",
    "version",
    "block_reference",
    "block_type",
    "theme",
    "text",
)


@dataclass(frozen=True)
class MarkdownCorpusExportSummary:
    scanned_sources: int
    exported_sources: int
    exported_blocks: int
    blocked_sources: int


def export_markdown_sources_to_csv(
    source_root: Path,
    output_path: Path,
) -> MarkdownCorpusExportSummary:
    source_paths = find_source_corpus_files(source_root)
    rows: list[dict[str, str]] = []
    exported_sources = 0
    blocked_sources = 0

    for source_path in source_paths:
        report = validate_source_corpus_file(source_path)
        if not report.is_indexable:
            blocked_sources += 1
            continue

        blocks = load_markdown_source_blocks(source_path)
        exported_sources += 1
        rows.extend(_build_rows(blocks))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CORPUS_EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return MarkdownCorpusExportSummary(
        scanned_sources=len(source_paths),
        exported_sources=exported_sources,
        exported_blocks=len(rows),
        blocked_sources=blocked_sources,
    )


def _build_rows(blocks: tuple[RagCorpusBlock, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for corpus_block in blocks:
        rows.append(
            {
                "source_id": corpus_block.metadata.title,
                "source_type": corpus_block.metadata.source_type.value,
                "title": corpus_block.metadata.title,
                "version": corpus_block.metadata.version,
                "block_reference": corpus_block.block.reference,
                "block_type": corpus_block.block.block_type.value,
                "theme": corpus_block.block.heading or "",
                "text": corpus_block.block.text,
            }
        )
    return rows
