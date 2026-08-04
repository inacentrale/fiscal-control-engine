from app.rag_source.domain import RagSourceMetadata, RagSourceType

ACTIVE_FINANCE_LAW_YEAR = 2026


def is_fiscal_source_in_active_scope(metadata: RagSourceMetadata) -> bool:
    """Keep non-law sources and only the selected finance-law vintage.

    Applicability is still checked independently at query/rule resolution time;
    this scope prevents older finance laws from entering the active RAG corpus.
    """
    if metadata.source_type is not RagSourceType.LAW:
        return True
    return (
        metadata.applicable_from is not None
        and metadata.applicable_from.year == ACTIVE_FINANCE_LAW_YEAR
    )
