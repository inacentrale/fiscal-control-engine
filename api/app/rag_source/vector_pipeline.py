from app.rag_source.domain import RagChunk
from app.rag_source.embedding_provider import EmbeddingProvider
from app.rag_source.vector_index import EmbeddedChunk


def embed_chunks(
    chunks: tuple[RagChunk, ...],
    embedding_provider: EmbeddingProvider,
) -> tuple[EmbeddedChunk, ...]:
    vectors = embedding_provider.embed_texts(tuple(chunk.text for chunk in chunks))
    return tuple(
        EmbeddedChunk(chunk=chunk, vector=vector)
        for chunk, vector in zip(chunks, vectors, strict=True)
    )
