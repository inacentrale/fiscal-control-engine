import hashlib
from pathlib import Path

from app.rag_source.chunker import RagChunker
from app.rag_source.corpus_loader import load_rag_corpus_blocks
from app.rag_source.domain import RagSourceDocument, RagSourceStatus
from app.rag_source.lexical_retriever import LexicalRetriever

_CORPUS_PATH = (
    Path(__file__).parents[4] / "docs" / "reference" / "rag-mini-corpus.csv"
)


def test_out_of_scope_section_is_retrievable_from_real_mini_corpus() -> None:
    corpus_blocks = load_rag_corpus_blocks(_CORPUS_PATH)
    text = "\n".join(corpus_block.block.text for corpus_block in corpus_blocks)
    document = RagSourceDocument(
        metadata=corpus_blocks[0].metadata,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        status=RagSourceStatus.ACTIVE,
    )
    chunks = RagChunker().chunk(
        document=document,
        blocks=tuple(corpus_block.block for corpus_block in corpus_blocks),
    )

    results = LexicalRetriever().search(
        query="ecarter une charge bancaire du perimetre RAS",
        chunks=chunks,
    )

    assert results
    assert results[0].chunk.section_reference == "PROC-001-S6"


def test_out_of_scope_section_covers_tax_versus_supplier_prestation_question() -> None:
    corpus_blocks = load_rag_corpus_blocks(_CORPUS_PATH)
    text = "\n".join(corpus_block.block.text for corpus_block in corpus_blocks)
    document = RagSourceDocument(
        metadata=corpus_blocks[0].metadata,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        status=RagSourceStatus.ACTIVE,
    )
    chunks = RagChunker().chunk(
        document=document,
        blocks=tuple(corpus_block.block for corpus_block in corpus_blocks),
    )

    results = LexicalRetriever().search(
        query=(
            "pourquoi une taxe ou impot n'est pas une prestation fournisseur"
        ),
        chunks=chunks,
    )

    assert results
    assert results[0].chunk.section_reference == "PROC-001-S6"
