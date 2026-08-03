from pathlib import Path

from app.rag_source.chunker import chunk_corpus_blocks
from app.rag_source.domain import RagSourceType
from app.rag_source.embedding_provider import EmbeddingProvider
from app.rag_source.embedding_provider_factory import create_embedding_provider
from app.rag_source.markdown_source_loader import load_markdown_source_blocks
from app.rag_source.source_corpus_validator import (
    find_source_corpus_files,
    validate_source_corpus_file,
)
from app.rag_source.vector_index import InMemoryVectorIndex, VectorSearchResult
from app.rag_source.vector_pipeline import embed_chunks


class FiscalVectorRetriever:
    """Index and query validated fiscal Markdown sources.

    Calculation rules remain outside this component. Retrieved chunks only
    provide sourced context and justification for consumers such as an LLM.
    """

    def __init__(
        self,
        source_root: Path,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        if not source_root.is_dir():
            raise ValueError("source_root must be an existing directory")

        corpus_blocks = tuple(
            block
            for source_path in find_source_corpus_files(source_root)
            if validate_source_corpus_file(source_path).is_indexable
            for block in load_markdown_source_blocks(source_path)
            if block.metadata.domain == "fiscal"
        )
        if not corpus_blocks:
            raise ValueError("no validated fiscal source is available for indexing")

        chunks = chunk_corpus_blocks(corpus_blocks)
        self._embedding_provider = embedding_provider
        self._index = InMemoryVectorIndex(
            embed_chunks(chunks=chunks, embedding_provider=embedding_provider),
        )
        self._indexed_chunk_count = len(chunks)
        self._indexed_source_count = len(
            {chunk.source_metadata.source_path for chunk in chunks},
        )

    @property
    def indexed_chunk_count(self) -> int:
        return self._indexed_chunk_count

    @property
    def indexed_source_count(self) -> int:
        return self._indexed_source_count

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> tuple[VectorSearchResult, ...]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")
        candidates = self._index.search(
            query_vector=self._embedding_provider.embed_text(normalized_query),
            limit=self._indexed_chunk_count,
        )
        ranked = sorted(
            candidates,
            key=lambda result: (
                -result.score,
                _source_authority_rank(result.chunk.source_metadata.source_type),
                result.chunk.chunk_reference,
            ),
        )
        return tuple(ranked[:limit])


def create_fiscal_vector_retriever(
    source_root: Path,
    provider_name: str,
    model_name: str,
) -> FiscalVectorRetriever:
    return FiscalVectorRetriever(
        source_root=source_root,
        embedding_provider=create_embedding_provider(
            provider_name=provider_name,
            model_name=model_name,
        ),
    )


def _source_authority_rank(source_type: RagSourceType) -> int:
    ranks = {
        RagSourceType.TAX_CODE: 0,
        RagSourceType.LAW: 1,
        RagSourceType.ADMINISTRATIVE_INSTRUCTION: 2,
        RagSourceType.OFFICIAL_FORM: 3,
    }
    return ranks.get(source_type, 4)
