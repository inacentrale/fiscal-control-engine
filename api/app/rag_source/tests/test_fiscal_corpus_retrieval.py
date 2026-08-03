from datetime import date
from pathlib import Path

from app.rag_source.chunker import chunk_corpus_blocks
from app.rag_source.domain import (
    RagApplicabilityStatus,
    RagChunk,
    RagSourceType,
)
from app.rag_source.lexical_retriever import LexicalRetriever
from app.rag_source.markdown_source_loader import load_markdown_source_blocks
from app.rag_source.source_corpus_validator import find_source_corpus_files

_FISCAL_ROOT = Path(__file__).parents[4] / "docs" / "source-corpus"


def test_loyers_question_retrieves_the_withholding_article() -> None:
    chunks = _all_fiscal_chunks()

    results = LexicalRetriever().search(
        query="Retrouver la source qui parle des loyers ou charges immobilieres.",
        chunks=chunks,
    )

    assert results
    assert results[0].chunk.section_reference == "articles 215 a 219"


def test_prestation_versus_goods_question_retrieves_article_206() -> None:
    chunks = _all_fiscal_chunks()

    results = LexicalRetriever().search(
        query=(
            "Retrouver la source utile pour differencier achat de "
            "marchandises et prestation de service."
        ),
        chunks=chunks,
    )

    assert results
    assert results[0].chunk.section_reference == "article 206"


def test_official_forms_are_loaded_as_structure_sources_with_official_urls() -> None:
    form_paths = sorted((_FISCAL_ROOT / "fiscal").glob("*-official-form.md"))
    blocks = tuple(
        block
        for form_path in form_paths
        for block in load_markdown_source_blocks(form_path)
    )

    assert len(form_paths) == 4
    assert len(blocks) == 8
    assert all(
        block.metadata.source_type is RagSourceType.OFFICIAL_FORM
        for block in blocks
    )
    assert all(
        block.metadata.applicability_status
        is RagApplicabilityStatus.NOT_STATED
        for block in blocks
    )
    assert all(
        block.metadata.source_url
        and block.metadata.source_url.startswith("https://dgi.bf/")
        for block in blocks
    )


def test_finance_law_sources_are_versioned_and_period_bounded() -> None:
    law_paths = sorted((_FISCAL_ROOT / "fiscal").glob("bf-finance-law-*.md"))
    blocks = tuple(
        block
        for law_path in law_paths
        for block in load_markdown_source_blocks(law_path)
    )

    assert len(law_paths) == 3
    assert len(blocks) == 6
    assert all(block.metadata.source_type is RagSourceType.LAW for block in blocks)
    assert all(
        block.metadata.applicability_status is RagApplicabilityStatus.CONFIRMED
        for block in blocks
    )
    assert {block.metadata.applicable_from for block in blocks} == {
        date(2024, 1, 1),
        date(2025, 1, 1),
        date(2026, 1, 1),
    }
    assert all(block.metadata.source_url for block in blocks)


def test_administrative_instructions_are_indexed_as_context_sources() -> None:
    instruction_paths = sorted(
        (_FISCAL_ROOT / "fiscal").glob("*-administrative-instruction.md"),
    )
    blocks = tuple(
        block
        for instruction_path in instruction_paths
        for block in load_markdown_source_blocks(instruction_path)
    )

    assert len(instruction_paths) == 3
    assert len(blocks) == 5
    assert all(
        block.metadata.source_type is RagSourceType.ADMINISTRATIVE_INSTRUCTION
        for block in blocks
    )
    assert all(block.metadata.source_url for block in blocks)


def _all_fiscal_chunks() -> tuple[RagChunk, ...]:
    validated_sources = [
        path
        for path in find_source_corpus_files(_FISCAL_ROOT)
        if path.parent.name == "fiscal"
    ]
    corpus_blocks = tuple(
        block
        for source_path in validated_sources
        for block in load_markdown_source_blocks(source_path)
    )
    return chunk_corpus_blocks(corpus_blocks)
