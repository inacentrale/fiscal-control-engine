import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from unicodedata import normalize

from app.rag_source.chunker import chunk_corpus_blocks
from app.rag_source.domain import RagChunk, RagSourceMetadata
from app.rag_source.fiscal_source_scope import is_fiscal_source_in_active_scope
from app.rag_source.fiscal_vector_retriever import FiscalVectorRetriever
from app.rag_source.lexical_retriever import LexicalRetriever, LexicalSearchResult
from app.rag_source.markdown_source_loader import load_markdown_source_blocks
from app.rag_source.source_corpus_validator import (
    find_source_corpus_files,
    validate_source_corpus_file,
)


@dataclass(frozen=True)
class TaxRagCitation:
    article_or_section: str
    passage: str
    title: str
    version: str
    source_url: str | None
    source_sha256: str
    score: float
    applicability_status: str
    applicable_from: str | None
    applicable_to: str | None


@dataclass(frozen=True)
class TaxRagQueryResult:
    query: str
    as_of_date: str | None
    citations: tuple[TaxRagCitation, ...]
    indexed_source_count: int
    retrieval_mode: str
    retrieval_policy_version: str = "tax-rag-hybrid-rerank-v1"
    decision_status: str = "retrieval_only_no_tax_decision"


class TaxRagQueryService:
    def __init__(
        self,
        source_root: Path,
        *,
        vector_retriever: FiscalVectorRetriever | None = None,
    ) -> None:
        if not source_root.is_dir():
            raise ValueError("tax RAG source root must be an existing directory")
        candidate_source_files = tuple(
            path
            for path in find_source_corpus_files(source_root)
            if validate_source_corpus_file(path).is_indexable
        )
        blocks = tuple(
            block
            for source_path in candidate_source_files
            for block in load_markdown_source_blocks(source_path)
            if block.metadata.domain == "fiscal"
            and is_fiscal_source_in_active_scope(block.metadata)
        )
        if not blocks:
            raise ValueError("no validated fiscal source is available")
        self._chunks = chunk_corpus_blocks(blocks)
        self._indexed_source_count = len(
            {block.metadata.source_path for block in blocks}
        )
        self._vector_retriever = vector_retriever

    def query(
        self,
        query: str,
        *,
        limit: int = 5,
        as_of_date: date | None = None,
    ) -> TaxRagQueryResult:
        normalized_query = " ".join(query.split())
        if not normalized_query:
            raise ValueError("tax RAG query must not be empty")
        if not 1 <= limit <= 5:
            raise ValueError("tax RAG result limit must be between 1 and 5")
        lexical_matches = LexicalRetriever().search(
            normalized_query,
            self._chunks,
            limit=len(self._chunks),
        )
        matches = self._rank_matches(normalized_query, lexical_matches, limit)
        citations = tuple(
            TaxRagCitation(
                article_or_section=chunk.section_reference,
                passage=chunk.text[:1200],
                title=chunk.source_metadata.title,
                version=chunk.source_metadata.version,
                source_url=chunk.source_metadata.source_url,
                source_sha256=chunk.source_text_sha256,
                score=score,
                applicability_status=_applicability(
                    chunk.source_metadata, as_of_date
                ),
                applicable_from=_date_text(
                    chunk.source_metadata.applicable_from
                ),
                applicable_to=_date_text(chunk.source_metadata.applicable_to),
            )
            for chunk, score in matches
        )
        return TaxRagQueryResult(
            query=normalized_query,
            as_of_date=_date_text(as_of_date),
            citations=citations,
            indexed_source_count=self._indexed_source_count,
            retrieval_mode=(
                "lexical_vector_rerank"
                if self._vector_retriever is not None
                else "lexical"
            ),
        )

    def _rank_matches(
        self,
        query: str,
        lexical_matches: tuple[LexicalSearchResult, ...],
        limit: int,
    ) -> tuple[tuple[RagChunk, float], ...]:
        if self._vector_retriever is None:
            return tuple(
                (
                    result.chunk,
                    _adjusted_lexical_score(query, result.chunk, result.score),
                )
                for result in sorted(
                    lexical_matches,
                    key=lambda item: (
                        -_adjusted_lexical_score(query, item.chunk, item.score),
                        item.chunk.sequence,
                    ),
                )[:limit]
            )
        if not lexical_matches:
            # Semantic retrieval reranks lexical evidence; it cannot bypass the
            # deterministic refusal when the question has no lexical anchor.
            return ()
        vector_matches = self._vector_retriever.search(
            query,
            limit=self._vector_retriever.indexed_chunk_count,
        )
        vector_rank = {
            result.chunk.chunk_reference: rank
            for rank, result in enumerate(vector_matches, start=1)
        }
        scored = tuple(
            (
                result.chunk,
                _reciprocal_rank(rank)
                + 2 * _reciprocal_rank(
                    vector_rank.get(
                        result.chunk.chunk_reference,
                        self._vector_retriever.indexed_chunk_count + 1,
                    )
                ),
            )
            for rank, result in enumerate(lexical_matches, start=1)
        )
        return tuple(
            (
                (chunk, _adjusted_lexical_score(query, chunk, score))
                for chunk, score in sorted(
                    scored,
                    key=lambda item: (
                        -_adjusted_lexical_score(query, item[0], item[1]),
                        item[0].sequence,
                    ),
                )[:limit]
            )
        )


def _adjusted_lexical_score(query: str, chunk: RagChunk, base_score: float) -> float:
    query_text = _normalized_search_text(query)
    chunk_text = _normalized_search_text(
        " ".join(
            (
                chunk.source_metadata.title,
                chunk.source_metadata.version,
                chunk.section_reference,
                chunk.text,
            )
        )
    )
    score = float(base_score)
    for year in re.findall(r"\b20\d{2}\b", query_text):
        if year in chunk_text:
            score += 3
    if "ifu" in query_text and "ifu" in chunk_text:
        score += 2
    if "taux" in query_text and "taux" in chunk_text:
        score += 1
    asks_resident = "resident" in query_text and "non resident" not in query_text
    if asks_resident and "non resident" in chunk_text:
        score -= 4
    asks_non_resident = "non resident" in query_text
    if asks_non_resident and "non resident" in chunk_text:
        score += 2
    return score


def _normalized_search_text(value: str) -> str:
    normalized = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.findall(r"[a-z0-9]+", normalized.lower()))


def _applicability(metadata: RagSourceMetadata, as_of_date: date | None) -> str:
    status = metadata.applicability_status.value
    if as_of_date is None or status != "confirmed":
        return status
    if metadata.applicable_from is not None and as_of_date < metadata.applicable_from:
        return "outside_requested_date"
    if metadata.applicable_to is not None and as_of_date > metadata.applicable_to:
        return "outside_requested_date"
    return "confirmed_for_requested_date"


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _reciprocal_rank(rank: int) -> float:
    return 1.0 / (60 + rank)
