import pytest

from app.rag_source.embedding_provider import DeterministicHashEmbeddingProvider
from app.rag_source.embedding_provider_factory import create_embedding_provider
from app.rag_source.sentence_transformers_provider import (
    SentenceTransformersEmbeddingProvider,
)


def test_create_embedding_provider_returns_deterministic_provider() -> None:
    provider = create_embedding_provider(
        provider_name="deterministic",
        model_name="unused",
    )

    assert isinstance(provider, DeterministicHashEmbeddingProvider)


def test_create_embedding_provider_returns_sentence_transformers_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.rag_source.embedding_provider_factory."
        "SentenceTransformersEmbeddingProvider",
        lambda model_name: FakeProvider(model_name),
    )

    provider = create_embedding_provider(
        provider_name="sentence-transformers",
        model_name="test-model",
    )

    assert isinstance(provider, FakeProvider)
    assert provider.model_name == "test-model"


def test_create_embedding_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="unknown embedding provider"):
        create_embedding_provider(provider_name="cloud", model_name="unused")


class FakeProvider(SentenceTransformersEmbeddingProvider):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
