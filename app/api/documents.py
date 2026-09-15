import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.security import OrganizationContext, get_current_org, get_current_user
from app.services.document_store import save_document_and_chunks
from app.services.langchain_ingest import LangChainIngestionError, ingest_pdf
from db.connection import DatabaseError, get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("uploaded_docs")
def _http_for_pipeline_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LangChainIngestionError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
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
async def upload_document(
    file: UploadFile,
    username: str = Depends(get_current_user),
    organization: OrganizationContext = Depends(get_current_org),
):
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
    try:
        chunks = ingest_pdf(saved_path)

        if not chunks:
            document_id, stored = save_document_and_chunks(
                filename, [], organization.org_id
            )
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

        document_id, stored = save_document_and_chunks(
            filename, chunks, organization.org_id
        )
    except (LangChainIngestionError, DatabaseError) as exc:
        raise _http_for_pipeline_error(exc) from exc

    logger.info("Finished processing %s document_id=%s chunks=%s", filename, document_id, stored)
    return {
        "filename": filename,
        "document_id": document_id,
        "total_chunks_created": stored,
    }


@router.get("/documents")
def list_documents(
    username: str = Depends(get_current_user),
    organization: OrganizationContext = Depends(get_current_org),
):
    """Return documents belonging to the authenticated organization."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT filename, id, uploaded_at
                FROM documents
                WHERE org_id = %s
                ORDER BY uploaded_at DESC
                """,
                (organization.org_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"filename": filename, "document_id": document_id, "timestamp": uploaded_at}
        for filename, document_id, uploaded_at in rows
    ]
