from app.routers.agent import DEFAULT_AGENT_TOOLS


def test_default_agent_tools_include_accounting_entry_reconstruction() -> None:
    assert "reconstruct_accounting_entry" in DEFAULT_AGENT_TOOLS
