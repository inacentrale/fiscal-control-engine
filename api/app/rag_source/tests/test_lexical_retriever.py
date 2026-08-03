from app.rag_source.domain import (
    RagChunk,
    RagSourceMetadata,
    RagSourceOrigin,
    RagSourceType,
    RagTextBlockType,
)
from app.rag_source.lexical_retriever import LexicalRetriever


def test_retriever_returns_best_matching_chunks() -> None:
    chunks = (
        _chunk(
            1,
            "PROC-001-S4",
            "citation source",
            "Toute explication cite une source.",
        ),
        _chunk(
            2,
            "PROC-001-S5",
            "confidentialite",
            "Les logs ne doivent pas exposer les donnees sensibles.",
        ),
    )

    results = LexicalRetriever().search(
        query="comment citer une source dans le rapport",
        chunks=chunks,
    )

    assert [result.chunk.chunk_reference for result in results] == [
        "Procedure interne RAG et revue fiscale:PROC-001-S4:1",
    ]
    assert results[0].score > 0
    assert "source" in results[0].matched_terms


def test_retriever_limits_results() -> None:
    chunks = (
        _chunk(1, "A", "source", "source citation rapport"),
        _chunk(2, "B", "source", "source rapport"),
        _chunk(3, "C", "source", "source"),
    )

    results = LexicalRetriever().search(
        query="source rapport",
        chunks=chunks,
        limit=2,
    )

    assert len(results) == 2
    assert [result.chunk.sequence for result in results] == [1, 2]


def test_retriever_returns_empty_results_when_query_has_no_overlap() -> None:
    chunks = (
        _chunk(
            1,
            "PROC-001-S4",
            "citation source",
            "Toute explication cite une source.",
        ),
    )

    results = LexicalRetriever().search(
        query="taux exact non resident",
        chunks=chunks,
    )

    assert results == ()


def test_retriever_rejects_empty_query() -> None:
    results = LexicalRetriever().search(
        query=" ",
        chunks=(_chunk(1, "PROC-001-S4", "citation", "source"),),
    )

    assert results == ()


def _chunk(
    sequence: int,
    section_reference: str,
    heading: str,
    text: str,
) -> RagChunk:
    return RagChunk(
        sequence=sequence,
        chunk_reference=(
            f"Procedure interne RAG et revue fiscale:{section_reference}:{sequence}"
        ),
        text=f"{heading}\n{text}",
        section_reference=section_reference,
        block_type=RagTextBlockType.SECTION,
        source_metadata=RagSourceMetadata(
            domain="compliance",
            source_type=RagSourceType.INTERNAL_PROCEDURE,
            title="Procedure interne RAG et revue fiscale",
            version="2026-07-28",
            language="fr",
            origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
            source_path="docs/reference/rag-mini-corpus.csv",
            themes=(heading,),
        ),
        source_text_sha256="abc123",
    )
