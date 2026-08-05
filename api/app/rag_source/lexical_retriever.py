import re
from dataclasses import dataclass
from unicodedata import normalize

from app.rag_source.domain import RagChunk

MIN_TERM_LENGTH = 3
_STOPWORDS = frozenset(
    {
        "les",
        "des",
        "une",
        "un",
        "par",
        "qui",
        "que",
        "quoi",
        "dont",
        "pour",
        "dans",
        "sur",
        "sous",
        "entre",
        "avec",
        "sans",
        "sont",
        "est",
        "etre",
        "ete",
        "ces",
        "cet",
        "cette",
        "ceux",
        "cela",
        "leur",
        "leurs",
        "tout",
        "toute",
        "tous",
        "toutes",
        "mais",
        "comme",
        "donc",
        "alors",
        "ainsi",
        "aussi",
        "meme",
        "memes",
        "ils",
        "elle",
        "elles",
        "nous",
        "vous",
        "plus",
        "afin",
        "vers",
        "chez",
        "lors",
        "apres",
        "avant",
    },
)


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
        for term in re.findall(r"[a-z0-9]+", normalized.lower())
        if len(term) >= MIN_TERM_LENGTH and term not in _STOPWORDS
    }
    return tuple(sorted(terms))
