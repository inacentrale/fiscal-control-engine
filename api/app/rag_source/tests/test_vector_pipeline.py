from app.rag_source.domain import (
    RagChunk,
    RagSourceMetadata,
    RagSourceOrigin,
    RagSourceType,
    RagTextBlockType,
)
from app.rag_source.embedding_provider import DeterministicHashEmbeddingProvider
from app.rag_source.vector_index import InMemoryVectorIndex
from app.rag_source.vector_pipeline import embed_chunks


def test_embed_chunks_builds_searchable_vector_index_inputs() -> None:
    provider = DeterministicHashEmbeddingProvider(dimensions=8)
    chunks = (
        _chunk(1, "citation source"),
        _chunk(2, "confidentialite donnees"),
    )

    embedded_chunks = embed_chunks(chunks=chunks, embedding_provider=provider)
    query_vector = provider.embed_text("citation source")
    results = InMemoryVectorIndex(embedded_chunks).search(query_vector=query_vector)

    assert len(embedded_chunks) == 2
    assert results[0].chunk.sequence == 1


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
