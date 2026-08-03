from pathlib import Path

from app.rag_source.corpus_loader import load_rag_corpus_blocks
from app.rag_source.domain import RagSourceType, RagTextBlockType

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_load_rag_corpus_blocks_from_csv() -> None:
    blocks = load_rag_corpus_blocks(FIXTURES_DIR / "rag-mini-corpus.csv")

    assert len(blocks) == 2
    assert blocks[0].metadata.domain == "compliance"
    assert blocks[0].metadata.source_type is RagSourceType.INTERNAL_PROCEDURE
    assert blocks[0].block.block_type is RagTextBlockType.SECTION
    assert blocks[0].block.reference == "PROC-001-S1"
    assert blocks[0].block.heading == "decision humaine"


def test_load_rag_corpus_blocks_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad-corpus.csv"
    path.write_text("source_id,title\nPROC-001,Procedure\n", encoding="utf-8")

    try:
        load_rag_corpus_blocks(path)
    except ValueError as exc:
        assert "missing corpus columns" in str(exc)
    else:
        raise AssertionError("missing columns should raise ValueError")
