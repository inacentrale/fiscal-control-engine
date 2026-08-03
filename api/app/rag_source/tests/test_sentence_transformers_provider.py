import pytest

from app.rag_source.sentence_transformers_provider import (
    MissingSentenceTransformersDependencyError,
    SentenceTransformersEmbeddingProvider,
)


def test_sentence_transformers_provider_uses_injected_model() -> None:
    provider = SentenceTransformersEmbeddingProvider(model=FakeSentenceModel())

    assert provider.embed_text("citation source") == (15.0, 16.0)
    assert provider.embed_texts(("a", "ab")) == ((1.0, 2.0), (2.0, 3.0))


def test_sentence_transformers_provider_requires_model_or_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_import_error(_: str) -> None:
        raise ImportError("missing")

    monkeypatch.setattr(
        "app.rag_source.sentence_transformers_provider.import_module",
        raise_import_error,
    )

    with pytest.raises(MissingSentenceTransformersDependencyError):
        SentenceTransformersEmbeddingProvider(model_name="test-model")


class FakeSentenceModel:
    def encode(
        self,
        texts: str | list[str],
        normalize_embeddings: bool,
    ) -> list[float] | list[list[float]]:
        assert normalize_embeddings is True
        if isinstance(texts, str):
            return [float(len(texts)), float(len(texts) + 1)]
        return [[float(len(text)), float(len(text) + 1)] for text in texts]
