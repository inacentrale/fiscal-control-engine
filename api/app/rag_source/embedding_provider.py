from hashlib import sha256
from typing import Protocol


class EmbeddingProvider(Protocol):
    def embed_text(self, text: str) -> tuple[float, ...]:
        pass

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        pass


class DeterministicHashEmbeddingProvider:
    def __init__(self, dimensions: int = 32) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions

    def embed_text(self, text: str) -> tuple[float, ...]:
        normalized_text = " ".join(text.lower().split())
        digest = sha256(normalized_text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < self._dimensions:
            values.extend(byte / 255 for byte in digest)
            digest = sha256(digest).digest()
        return tuple(values[: self._dimensions])

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(self.embed_text(text) for text in texts)
