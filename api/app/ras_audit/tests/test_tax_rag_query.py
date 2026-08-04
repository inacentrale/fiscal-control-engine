from datetime import date
from pathlib import Path

from app.rag_source.domain import RagSourceType
from app.rag_source.fiscal_vector_retriever import FiscalVectorRetriever
from app.rag_source.markdown_source_loader import load_markdown_source_blocks
from app.rag_source.source_corpus_validator import find_source_corpus_files
from app.ras_audit.tax_rag_query import TaxRagQueryService

SOURCES = Path("../docs/source-corpus/fiscal")


class NonResidentSemanticProvider:
    def embed_text(self, text: str) -> tuple[float, ...]:
        normalized = text.lower()
        if (
            "prestataire non resident" in normalized
            or "fournisseur non resident" in normalized
            or "art.210" in normalized
        ):
            return (1.0, 0.0)
        return (0.0, 1.0)

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(self.embed_text(text) for text in texts)


def test_returns_traceable_legal_citations_without_tax_decision() -> None:
    result = TaxRagQueryService(SOURCES).query(
        "Quelle retenue à la source s'applique aux prestataires résidents ?",
        limit=3,
        as_of_date=date(2026, 4, 10),
    )

    assert result.citations
    citation = result.citations[0]
    assert citation.article_or_section
    assert citation.passage
    assert citation.version
    assert citation.source_url is not None
    assert len(citation.source_sha256) == 64
    assert citation.score > 0
    assert result.decision_status == "retrieval_only_no_tax_decision"


def test_returns_empty_citations_for_unmatched_question() -> None:
    result = TaxRagQueryService(SOURCES).query("xylophone quantique")

    assert result.citations == ()


def test_active_rag_scope_keeps_only_finance_law_2026() -> None:
    result = TaxRagQueryService(SOURCES).query(
        "Prestataires residents : taux de 5 pour cent sans IFU",
        limit=5,
        as_of_date=date(2026, 4, 10),
    )

    cited_law_versions = {
        citation.version
        for citation in result.citations
        if "Loi de finances" in citation.title
    }
    assert cited_law_versions
    assert all("2026" in version for version in cited_law_versions)
    assert result.indexed_source_count == 14

    indexed_law_years = {
        block.metadata.applicable_from.year
        for path in find_source_corpus_files(SOURCES)
        for block in load_markdown_source_blocks(path)
        if block.metadata.source_type is RagSourceType.LAW
        and block.metadata.applicable_from is not None
    }
    assert indexed_law_years == {2024, 2025, 2026}


def test_hybrid_reranking_resolves_a_natural_language_lexical_ambiguity() -> None:
    question = (
        "Retrouver le passage qui traite des prestations realisees par un "
        "fournisseur non resident."
    )
    lexical = TaxRagQueryService(SOURCES).query(question, limit=1)
    hybrid = TaxRagQueryService(
        SOURCES,
        vector_retriever=FiscalVectorRetriever(
            SOURCES,
            NonResidentSemanticProvider(),
        ),
    ).query(question, limit=1)

    assert lexical.citations[0].article_or_section != "articles 210 et 211"
    assert hybrid.citations[0].article_or_section == "articles 210 et 211"
    assert hybrid.retrieval_mode == "lexical_vector_rerank"
    assert hybrid.retrieval_policy_version == "tax-rag-hybrid-rerank-v1"


def test_hybrid_mode_cannot_bypass_a_question_without_lexical_anchor() -> None:
    result = TaxRagQueryService(
        SOURCES,
        vector_retriever=FiscalVectorRetriever(
            SOURCES,
            NonResidentSemanticProvider(),
        ),
    ).query("xylophone quantique")

    assert result.citations == ()
