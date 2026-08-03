from pathlib import Path

import pytest

from app.rag_source.fiscal_vector_retriever import FiscalVectorRetriever


class SemanticTestEmbeddingProvider:
    def embed_text(self, text: str) -> tuple[float, ...]:
        normalized = text.lower()
        if "art.215" in normalized or "retenue sur loyer" in normalized:
            return (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if "vente de biens" in normalized or "vente de marchandises" in normalized:
            return (0.0, 1.0, 0.0, 0.0, 0.0, 0.0)
        if "art.317" in normalized or "taux tva" in normalized:
            return (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        if "art.112" in normalized or "bareme salaire" in normalized:
            return (0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        if "art.88" in normalized or "minimum forfaitaire" in normalized:
            return (0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        return (0.0, 0.0, 0.0, 0.0, 0.0, 1.0)

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(self.embed_text(text) for text in texts)


_SOURCE_ROOT = Path(__file__).parents[4] / "docs" / "source-corpus"


def test_retriever_indexes_validated_fiscal_sources_and_preserves_citation() -> None:
    retriever = FiscalVectorRetriever(
        source_root=_SOURCE_ROOT,
        embedding_provider=SemanticTestEmbeddingProvider(),
    )

    results = retriever.search("Quel texte encadre la retenue sur loyer ?")

    assert retriever.indexed_source_count == 16
    assert retriever.indexed_chunk_count == 37
    assert results[0].chunk.section_reference == "articles 215 a 219"
    assert results[0].chunk.source_metadata.version
    assert results[0].chunk.source_text_sha256


def test_retriever_vectorizes_the_query_for_semantic_search() -> None:
    retriever = FiscalVectorRetriever(
        source_root=_SOURCE_ROOT,
        embedding_provider=SemanticTestEmbeddingProvider(),
    )

    results = retriever.search("Distinguer une vente de marchandises d'un service")

    assert results[0].chunk.section_reference == "article 206"


@pytest.mark.parametrize(
    ("query", "expected_reference"),
    [
        ("Quel est le taux TVA ?", "article 317"),
        ("Quel bareme salaire faut-il appliquer ?", "article 112"),
        ("Comment calculer le minimum forfaitaire ?", "articles 88 a 90"),
    ],
)
def test_retriever_searches_the_main_declaration_tax_sources(
    query: str,
    expected_reference: str,
) -> None:
    retriever = FiscalVectorRetriever(
        source_root=_SOURCE_ROOT,
        embedding_provider=SemanticTestEmbeddingProvider(),
    )

    results = retriever.search(query)

    assert results[0].chunk.section_reference == expected_reference


def test_retriever_prefers_tax_code_over_form_at_equal_semantic_score() -> None:
    retriever = FiscalVectorRetriever(
        source_root=_SOURCE_ROOT,
        embedding_provider=SemanticTestEmbeddingProvider(),
    )

    results = retriever.search("Comment calculer le minimum forfaitaire ?")

    assert results[0].chunk.source_metadata.source_type.value == "tax_code"
    assert results[0].chunk.section_reference == "articles 88 a 90"


def test_retriever_rejects_a_directory_without_validated_sources() -> None:
    with pytest.raises(ValueError, match="no validated fiscal source"):
        FiscalVectorRetriever(
            source_root=Path(__file__).parent / "fixtures",
            embedding_provider=SemanticTestEmbeddingProvider(),
        )


def test_retriever_rejects_an_empty_query() -> None:
    retriever = FiscalVectorRetriever(
        source_root=_SOURCE_ROOT,
        embedding_provider=SemanticTestEmbeddingProvider(),
    )

    with pytest.raises(ValueError, match="query must not be empty"):
        retriever.search("  ")
