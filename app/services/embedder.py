import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


class EmbeddingError(Exception):
    """Raised when the embedding model cannot be loaded or used."""


def get_embedding_model():
    """Return a shared all-MiniLM-L6-v2 model, loading it on first use."""
    global _model
    if _model is None:
        try:
            logger.info("Loading embedding model %s", MODEL_NAME)
            _model = SentenceTransformer(MODEL_NAME)
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to load embedding model '{MODEL_NAME}'."
            ) from exc
    return _model


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Add an 'embedding' vector to each chunk dict. No-op for an empty list."""
    if not chunks:
        return chunks
    try:
        model = get_embedding_model()
        embeddings = model.encode([chunk["text"] for chunk in chunks])
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError("Failed to generate embeddings.") from exc

    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
    logger.info("Generated embeddings for %s chunks (dim=%s)", len(chunks), embeddings.shape[1])
    return chunks
