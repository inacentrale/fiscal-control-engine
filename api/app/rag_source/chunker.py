from app.rag_source.constants import (
    DEFAULT_CHUNK_MAX_WORDS,
    DEFAULT_CHUNK_OVERLAP_WORDS,
)
from app.rag_source.domain import RagChunk, RagSourceDocument, RagTextBlock


class RagChunker:
    def __init__(
        self,
        max_words: int = DEFAULT_CHUNK_MAX_WORDS,
        overlap_words: int = DEFAULT_CHUNK_OVERLAP_WORDS,
    ) -> None:
        if max_words < 1:
            raise ValueError("max_words must be positive")
        if overlap_words < 0 or overlap_words >= max_words:
            raise ValueError("overlap_words must be lower than max_words")
        self._max_words = max_words
        self._overlap_words = overlap_words

    def chunk(
        self,
        document: RagSourceDocument,
        blocks: tuple[RagTextBlock, ...],
    ) -> tuple[RagChunk, ...]:
        if not document.can_be_indexed:
            raise ValueError("document must be active before chunking")

        chunks: list[RagChunk] = []
        for block in blocks:
            for text_part in self._split_text(block.searchable_text):
                sequence = len(chunks) + 1
                chunks.append(
                    RagChunk(
                        sequence=sequence,
                        chunk_reference=self._build_chunk_reference(
                            document=document,
                            block=block,
                            sequence=sequence,
                        ),
                        text=text_part,
                        section_reference=block.reference,
                        block_type=block.block_type,
                        source_metadata=document.metadata,
                        source_text_sha256=document.text_sha256,
                    )
                )

        return tuple(chunks)

    def _split_text(self, text: str) -> tuple[str, ...]:
        words = text.split()
        if len(words) <= self._max_words:
            return (text.strip(),)

        parts: list[str] = []
        step = self._max_words - self._overlap_words
        start = 0
        while start < len(words):
            end = start + self._max_words
            parts.append(" ".join(words[start:end]))
            if end >= len(words):
                break
            start += step

        return tuple(parts)

    def _build_chunk_reference(
        self,
        document: RagSourceDocument,
        block: RagTextBlock,
        sequence: int,
    ) -> str:
        return f"{document.metadata.title}:{block.reference}:{sequence}"


FiscalChunker = RagChunker
