import hashlib
from pathlib import Path

from app.rag_source.chunker import RagChunker
from app.rag_source.corpus_loader import load_rag_corpus_blocks
from app.rag_source.domain import RagSourceDocument, RagSourceStatus
from app.rag_source.lexical_retriever import LexicalRetriever

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_local_retrieval_flow_returns_expected_chunk_from_corpus() -> None:
    corpus_blocks = load_rag_corpus_blocks(FIXTURES_DIR / "rag-mini-corpus.csv")
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
        query="expliquer avec une source citee",
        chunks=chunks,
    )

    assert [result.chunk.chunk_reference for result in results] == [
        "Procedure interne RAG et revue fiscale:PROC-001-S4:2",
    ]
