import logging
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_embeddings = None
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


class LangChainIngestionError(Exception):
    """Raised when LangChain cannot load, split, or embed a PDF."""


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        try:
            _embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
        except Exception as exc:
            raise LangChainIngestionError(
                f"Failed to load embedding model '{MODEL_NAME}'."
            ) from exc
    return _embeddings


def ingest_pdf(pdf_path: Path) -> list[dict]:
    """Load, split, and embed a PDF using LangChain components."""
    try:
        documents = PyPDFLoader(str(pdf_path)).load()
    except Exception as exc:
        raise LangChainIngestionError(f"Failed to load PDF: {pdf_path}") from exc

    chunks = _splitter.split_documents(documents)
    chunks = [chunk for chunk in chunks if chunk.page_content.strip()]
    if not chunks:
        logger.warning("No text chunks created from %s", pdf_path)
        return []

    try:
        embeddings = _get_embeddings().embed_documents(
            [chunk.page_content for chunk in chunks]
        )
    except Exception as exc:
        raise LangChainIngestionError("Failed to embed document chunks.") from exc

    if embeddings and len(embeddings[0]) != EMBEDDING_DIM:
        raise LangChainIngestionError(
            f"Document embeddings have dimension {len(embeddings[0])}; "
            f"expected {EMBEDDING_DIM}."
        )

    records = []
    for chunk_index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        records.append(
            {
                "text": chunk.page_content,
                "page_number": int(chunk.metadata.get("page", 0)) + 1,
                "chunk_index": chunk_index,
                "embedding": embedding,
            }
        )

    logger.info(
        "LangChain ingestion created %s embedded chunks from %s",
        len(records),
        pdf_path,
    )
    return records
