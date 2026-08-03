import pytest

from app.rag_source.chunker import FiscalChunker, RagChunker
from app.rag_source.domain import (
    FiscalSourceDocument,
    FiscalSourceMetadata,
    FiscalSourceOrigin,
    FiscalSourceStatus,
    FiscalSourceType,
    FiscalTextBlock,
    FiscalTextBlockType,
    RagChunk,
    RagSourceDocument,
    RagSourceMetadata,
    RagSourceOrigin,
    RagSourceStatus,
    RagSourceType,
    RagTextBlock,
    RagTextBlockType,
)


def test_chunker_creates_one_chunk_per_short_structured_block() -> None:
    document = _active_document()
    blocks = (
        FiscalTextBlock(
            block_type=FiscalTextBlockType.ARTICLE,
            reference="Article 84",
            heading="Retenue a la source",
            text=(
                "Les sommes payees aux prestataires non residents "
                "sont soumises a RAS."
            ),
        ),
        FiscalTextBlock(
            block_type=FiscalTextBlockType.PARAGRAPH,
            reference="Article 84 alinea 2",
            heading=None,
            text="La retenue est verifiee avant declaration.",
        ),
    )

    chunks = RagChunker(max_words=20, overlap_words=3).chunk(document, blocks)

    assert [chunk.sequence for chunk in chunks] == [1, 2]
    assert isinstance(chunks[0], RagChunk)
    assert chunks[0].chunk_reference == "Code general des impots:Article 84:1"
    assert chunks[0].source_metadata == document.metadata
    assert chunks[0].source_text_sha256 == document.text_sha256
    assert chunks[0].section_reference == "Article 84"
    assert chunks[0].text == (
        "Retenue a la source\n"
        "Les sommes payees aux prestataires non residents sont soumises a RAS."
    )


def test_chunker_splits_long_block_with_overlap() -> None:
    document = _active_document()
    words = tuple(f"mot{i}" for i in range(1, 26))
    block = RagTextBlock(
        block_type=RagTextBlockType.ARTICLE,
        reference="Article 100",
        heading=None,
        text=" ".join(words),
    )

    chunks = RagChunker(max_words=10, overlap_words=2).chunk(document, (block,))

    assert [chunk.sequence for chunk in chunks] == [1, 2, 3]
    assert chunks[0].text == " ".join(words[0:10])
    assert chunks[1].text == " ".join(words[8:18])
    assert chunks[2].text == " ".join(words[16:25])


def test_chunker_rejects_inactive_document() -> None:
    document = RagSourceDocument(
        metadata=_metadata(),
        text_sha256="abc123",
        status=RagSourceStatus.PENDING_REVIEW,
    )
    block = RagTextBlock(
        block_type=RagTextBlockType.ARTICLE,
        reference="Article 84",
        heading=None,
        text="Texte fiscal.",
    )

    with pytest.raises(ValueError, match="active"):
        RagChunker().chunk(document, (block,))


def test_chunker_rejects_invalid_window_configuration() -> None:
    with pytest.raises(ValueError, match="overlap_words"):
        RagChunker(max_words=10, overlap_words=10)


def test_text_block_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="text"):
        RagTextBlock(
            block_type=RagTextBlockType.ARTICLE,
            reference="Article 84",
            heading=None,
            text=" ",
        )


def test_fiscal_names_are_kept_as_compatibility_aliases() -> None:
    assert FiscalChunker is RagChunker
    assert FiscalTextBlock is RagTextBlock
    assert FiscalTextBlockType is RagTextBlockType
    assert FiscalSourceMetadata is RagSourceMetadata
    assert FiscalSourceDocument is RagSourceDocument
    assert FiscalSourceType is RagSourceType
    assert FiscalSourceOrigin is RagSourceOrigin
    assert FiscalSourceStatus is RagSourceStatus


def _metadata() -> RagSourceMetadata:
    return RagSourceMetadata(
        country="BF",
        source_type=RagSourceType.TAX_CODE,
        title="Code general des impots",
        version="2025",
        language="fr",
        origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
        source_path="docs/source/cgi-bf-2025.pdf",
        themes=("RAS",),
    )


def _active_document() -> RagSourceDocument:
    return RagSourceDocument(
        metadata=_metadata(),
        text_sha256="abc123",
        status=RagSourceStatus.ACTIVE,
    )
