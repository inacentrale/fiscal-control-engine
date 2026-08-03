from dataclasses import dataclass
from unicodedata import normalize

from app.rag_source.domain import RagChunk

MIN_TERM_LENGTH = 3


@dataclass(frozen=True)
class LexicalSearchResult:
    chunk: RagChunk
    score: int
    matched_terms: tuple[str, ...]


class LexicalRetriever:
    def search(
        self,
        query: str,
        chunks: tuple[RagChunk, ...],
        limit: int = 5,
    ) -> tuple[LexicalSearchResult, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")

        query_terms = _tokenize(query)
        if not query_terms:
            return ()

        results: list[LexicalSearchResult] = []
        for chunk in chunks:
            chunk_terms = _tokenize(chunk.text)
            matched_terms = tuple(
                term for term in query_terms if term in chunk_terms
            )
            if not matched_terms:
                continue
            results.append(
                LexicalSearchResult(
                    chunk=chunk,
                    score=len(matched_terms),
                    matched_terms=matched_terms,
                )
            )

        ordered_results = sorted(
            results,
            key=lambda result: (-result.score, result.chunk.sequence),
        )
        return tuple(ordered_results[:limit])


def _tokenize(value: str) -> tuple[str, ...]:
    normalized = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    terms = {
        term
        for term in normalized.lower().split()
        if len(term) >= MIN_TERM_LENGTH
    }
    return tuple(sorted(terms))
