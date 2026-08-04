from pathlib import Path

from app.agent.dashboard_service import _create_tax_rag_query_service


def test_tax_rag_index_is_reused_between_agent_executor_builds() -> None:
    source_root = str(Path("../docs/source-corpus/fiscal").resolve())
    _create_tax_rag_query_service.cache_clear()

    first = _create_tax_rag_query_service(source_root, "disabled", "unused")
    second = _create_tax_rag_query_service(source_root, "disabled", "unused")

    assert first is second
    assert _create_tax_rag_query_service.cache_info().hits == 1
