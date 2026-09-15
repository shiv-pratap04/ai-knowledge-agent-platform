import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.security import get_current_user
from app.services.chunker import chunk_pages
from app.services.document_store import save_document_and_chunks
from app.services.embedder import EmbeddingError, embed_chunks
from app.services.pdf_parser import InvalidPdfError, extract_text_from_pdf
from db.connection import DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("uploaded_docs")
documents = []


def _http_for_pipeline_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidPdfError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, EmbeddingError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model failed to load or encode text. Check the server logs.",
        )
    if isinstance(exc, DatabaseError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Postgres. Start it with: docker compose up -d",
        )
    logger.exception("Unexpected error while processing document")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to process the uploaded document.",
    )


@router.post("/documents")
async def upload_document(file: UploadFile, username: str = Depends(get_current_user)):
    """Save an uploaded PDF, then extract, chunk, embed, and store it."""
    UPLOAD_DIR.mkdir(exist_ok=True)

    filename = Path(file.filename or "unnamed").name
    saved_path = UPLOAD_DIR / filename
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    saved_path.write_bytes(contents)
    logger.info("Document uploaded by %s: %s (%s bytes)", username, filename, len(contents))

    record = {
        "filename": filename,
        "path": str(saved_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    documents.append(record)

    try:
        pages, near_empty = extract_text_from_pdf(saved_path)
        chunks = [] if near_empty else chunk_pages(pages)

        if near_empty or not chunks:
            document_id, stored = save_document_and_chunks(filename, [])
            logger.info("No chunks created for %s (document_id=%s)", filename, document_id)
            return {
                "filename": filename,
                "document_id": document_id,
                "total_chunks_created": stored,
                "message": (
                    "Little to no text extracted - this PDF might be "
                    "scanned/image-based and need OCR. No chunks were created."
                ),
            }

        embed_chunks(chunks)
        document_id, stored = save_document_and_chunks(filename, chunks)
    except (InvalidPdfError, EmbeddingError, DatabaseError) as exc:
        raise _http_for_pipeline_error(exc) from exc

    logger.info("Finished processing %s document_id=%s chunks=%s", filename, document_id, stored)
    return {
        "filename": filename,
        "document_id": document_id,
        "total_chunks_created": stored,
    }


@router.get("/documents")
def list_documents(username: str = Depends(get_current_user)):
    """Return the in-memory list of uploads from this server process."""
    return documents
