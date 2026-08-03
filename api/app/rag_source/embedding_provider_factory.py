from app.rag_source.embedding_provider import (
    DeterministicHashEmbeddingProvider,
    EmbeddingProvider,
)
from app.rag_source.sentence_transformers_provider import (
    SentenceTransformersEmbeddingProvider,
)

DETERMINISTIC_PROVIDER = "deterministic"
SENTENCE_TRANSFORMERS_PROVIDER = "sentence-transformers"


def create_embedding_provider(
    provider_name: str,
    model_name: str,
) -> EmbeddingProvider:
    normalized_provider_name = provider_name.strip().lower()
    if normalized_provider_name == DETERMINISTIC_PROVIDER:
        return DeterministicHashEmbeddingProvider()
    if normalized_provider_name == SENTENCE_TRANSFORMERS_PROVIDER:
        return SentenceTransformersEmbeddingProvider(model_name=model_name)
    raise ValueError(f"unknown embedding provider: {provider_name}")
