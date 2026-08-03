from app.rag_source.embedding_provider import DeterministicHashEmbeddingProvider


def test_deterministic_embedding_provider_returns_stable_vectors() -> None:
    provider = DeterministicHashEmbeddingProvider(dimensions=8)

    first_vector = provider.embed_text("citation source")
    second_vector = provider.embed_text("citation source")

    assert first_vector == second_vector
    assert len(first_vector) == 8
    assert any(value != 0 for value in first_vector)


def test_deterministic_embedding_provider_embeds_batch() -> None:
    provider = DeterministicHashEmbeddingProvider(dimensions=4)

    vectors = provider.embed_texts(("citation source", "confidentialite"))

    assert len(vectors) == 2
    assert all(len(vector) == 4 for vector in vectors)
    assert vectors[0] != vectors[1]
