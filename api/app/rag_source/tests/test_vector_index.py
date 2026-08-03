import pytest

from app.rag_source.domain import (
    RagChunk,
    RagSourceMetadata,
    RagSourceOrigin,
    RagSourceType,
    RagTextBlockType,
)
from app.rag_source.vector_index import (
    EmbeddedChunk,
    InMemoryVectorIndex,
)


def test_vector_index_returns_most_similar_chunks() -> None:
    index = InMemoryVectorIndex(
        embedded_chunks=(
            EmbeddedChunk(chunk=_chunk(1, "citation source"), vector=(1.0, 0.0)),
            EmbeddedChunk(chunk=_chunk(2, "confidentialite"), vector=(0.0, 1.0)),
        )
    )

    results = index.search(query_vector=(0.9, 0.1), limit=2)

    assert [result.chunk.sequence for result in results] == [1, 2]
    assert results[0].score > results[1].score


def test_vector_index_filters_zero_similarity_results() -> None:
    index = InMemoryVectorIndex(
        embedded_chunks=(
            EmbeddedChunk(chunk=_chunk(1, "citation source"), vector=(1.0, 0.0)),
        )
    )

    assert index.search(query_vector=(0.0, 1.0)) == ()


def test_vector_index_rejects_dimension_mismatch() -> None:
    index = InMemoryVectorIndex(
        embedded_chunks=(
            EmbeddedChunk(chunk=_chunk(1, "citation source"), vector=(1.0, 0.0)),
        )
    )

    with pytest.raises(ValueError, match="dimension"):
        index.search(query_vector=(1.0, 0.0, 0.0))


def test_embedded_chunk_rejects_empty_vector() -> None:
    with pytest.raises(ValueError, match="vector"):
        EmbeddedChunk(chunk=_chunk(1, "citation source"), vector=())


def _chunk(sequence: int, text: str) -> RagChunk:
    return RagChunk(
        sequence=sequence,
        chunk_reference=f"source:section:{sequence}",
        text=text,
        section_reference="section",
        block_type=RagTextBlockType.SECTION,
        source_metadata=RagSourceMetadata(
            domain="compliance",
            source_type=RagSourceType.INTERNAL_PROCEDURE,
            title="source",
            version="2026",
            language="fr",
            origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
            source_path="docs/source.md",
            themes=("test",),
        ),
        source_text_sha256="abc123",
    )
