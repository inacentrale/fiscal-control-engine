from importlib import import_module
from typing import Any


class MissingSentenceTransformersDependencyError(RuntimeError):
    pass


class SentenceTransformersEmbeddingProvider:
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        model: Any | None = None,
    ) -> None:
        self._model = model if model is not None else self._load_model(model_name)

    def embed_text(self, text: str) -> tuple[float, ...]:
        encoded = self._model.encode(text, normalize_embeddings=True)
        return _to_vector(encoded)

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        encoded = self._model.encode(list(texts), normalize_embeddings=True)
        return tuple(_to_vector(vector) for vector in encoded)

    def _load_model(self, model_name: str) -> Any:
        try:
            module = import_module("sentence_transformers")
        except ImportError as exc:
            raise MissingSentenceTransformersDependencyError(
                "Install the optional embeddings dependencies to use "
                "SentenceTransformersEmbeddingProvider.",
            ) from exc
        return module.SentenceTransformer(model_name)


def _to_vector(value: Any) -> tuple[float, ...]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return tuple(float(item) for item in value)
