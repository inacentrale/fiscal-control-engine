from dataclasses import dataclass
from math import sqrt

from app.rag_source.domain import RagChunk


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk: RagChunk
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.vector:
            raise ValueError("vector must not be empty")


@dataclass(frozen=True)
class VectorSearchResult:
    chunk: RagChunk
    score: float


class InMemoryVectorIndex:
    def __init__(self, embedded_chunks: tuple[EmbeddedChunk, ...]) -> None:
        self._embedded_chunks = embedded_chunks

    def search(
        self,
        query_vector: tuple[float, ...],
        limit: int = 5,
    ) -> tuple[VectorSearchResult, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if not query_vector:
            raise ValueError("query_vector must not be empty")

        results: list[VectorSearchResult] = []
        for embedded_chunk in self._embedded_chunks:
            score = _cosine_similarity(query_vector, embedded_chunk.vector)
            if score <= 0:
                continue
            results.append(VectorSearchResult(chunk=embedded_chunk.chunk, score=score))

        ordered_results = sorted(
            results,
            key=lambda result: (-result.score, result.chunk.sequence),
        )
        return tuple(ordered_results[:limit])


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimension mismatch")

    left_norm = _norm(left)
    right_norm = _norm(right)
    if left_norm == 0 or right_norm == 0:
        return 0

    dot_product = sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=True)
    )
    return dot_product / (left_norm * right_norm)


def _norm(vector: tuple[float, ...]) -> float:
    return sqrt(sum(value * value for value in vector))
