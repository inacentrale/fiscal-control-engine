import pytest

from app.llm.model_registry import ModelRegistry, ModelSpec


def test_model_registry_parses_ordered_provider_chain() -> None:
    registry = ModelRegistry.from_chain(
        "openai:gpt-4.1-mini,anthropic:claude-sonnet,internal:controlled-response",
    )

    assert registry.primary == ModelSpec(
        provider_name="openai",
        model_name="gpt-4.1-mini",
    )
    assert registry.fallbacks == (
        ModelSpec(provider_name="anthropic", model_name="claude-sonnet"),
        ModelSpec(provider_name="internal", model_name="controlled-response"),
    )


def test_model_registry_rejects_empty_chain() -> None:
    with pytest.raises(ValueError, match="at least one model"):
        ModelRegistry.from_chain(" ")


def test_model_registry_rejects_malformed_entry() -> None:
    with pytest.raises(ValueError, match="provider:model"):
        ModelRegistry.from_chain("openai")


def test_model_registry_rejects_blank_provider_or_model() -> None:
    with pytest.raises(ValueError, match="provider and model"):
        ModelRegistry.from_chain("openai:")
