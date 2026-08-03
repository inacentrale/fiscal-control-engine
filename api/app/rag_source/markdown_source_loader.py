import re
from pathlib import Path

from app.rag_source.corpus_loader import RagCorpusBlock
from app.rag_source.domain import (
    RagSourceMetadata,
    RagSourceOrigin,
    RagSourceType,
    RagTextBlock,
    RagTextBlockType,
)
from app.rag_source.source_corpus_validator import validate_source_corpus_file

BLOCK_PATTERN = re.compile(
    r"- `block_reference`: `(?P<reference>[^`]+)`\s+"
    r"- `block_type`: `(?P<block_type>[^`]+)`\s+"
    r"- `theme`: `(?P<theme>[^`]+)`\s+"
    r"```text\s*(?P<text>.*?)\s*```",
    re.DOTALL,
)


def load_markdown_source_blocks(source_path: Path) -> tuple[RagCorpusBlock, ...]:
    report = validate_source_corpus_file(source_path)
    if not report.is_indexable:
        raise ValueError("source is not indexable")

    content = source_path.read_text(encoding="utf-8")
    metadata = _build_metadata(report.metadata, source_path)
    blocks = tuple(_build_block(match) for match in BLOCK_PATTERN.finditer(content))
    if not blocks:
        raise ValueError("source must contain at least one block")

    return tuple(
        RagCorpusBlock(metadata=metadata, block=block)
        for block in blocks
    )


def _build_metadata(
    raw_metadata: dict[str, str],
    source_path: Path,
) -> RagSourceMetadata:
    return RagSourceMetadata(
        domain=raw_metadata["domain"],
        country=raw_metadata.get("country"),
        source_type=RagSourceType(raw_metadata["source_type"]),
        title=raw_metadata["title"],
        version=raw_metadata["version"],
        language=raw_metadata["language"],
        origin=RagSourceOrigin(raw_metadata["origin"]),
        source_path=str(source_path),
        themes=_split_themes(raw_metadata["themes"]),
    )


def _build_block(match: re.Match[str]) -> RagTextBlock:
    text = match.group("text").strip()
    if not text:
        raise ValueError("block text is required")

    return RagTextBlock(
        block_type=RagTextBlockType(match.group("block_type").strip()),
        reference=match.group("reference"),
        heading=match.group("theme"),
        text=text,
    )


def _split_themes(value: str) -> tuple[str, ...]:
    themes = tuple(theme.strip() for theme in value.split(";") if theme.strip())
    if not themes:
        raise ValueError("themes must contain at least one value")
    return themes
