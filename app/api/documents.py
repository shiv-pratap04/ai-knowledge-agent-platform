import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.security import OrganizationContext, get_current_org, get_current_user
from app.services.document_store import create_document
from app.services.document_store import mark_document_failed
from app.services.document_tasks import process_document
from db.connection import DatabaseError, get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("uploaded_docs")
@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile,
    username: str = Depends(get_current_user),
    organization: OrganizationContext = Depends(get_current_org),
):
    """Save an uploaded PDF and enqueue asynchronous ingestion."""
    UPLOAD_DIR.mkdir(exist_ok=True)

    filename = Path(file.filename or "unnamed").name
    saved_path = UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    saved_path.write_bytes(contents)
    logger.info("Document uploaded by %s: %s (%s bytes)", username, filename, len(contents))

    try:
        document_id = create_document(filename, str(saved_path), organization.org_id)
        process_document.delay(document_id)
    except DatabaseError as exc:
        if "document_id" in locals():
            mark_document_failed(document_id, "Could not enqueue document processing.")
        saved_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not queue document processing.",
        ) from exc
    except Exception as exc:
        if "document_id" in locals():
            mark_document_failed(document_id, "Could not enqueue document processing.")
        saved_path.unlink(missing_ok=True)
        logger.exception("Could not enqueue document %s", filename)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not queue document processing.",
        ) from exc

    logger.info("Queued document %s document_id=%s", filename, document_id)
    return {
        "filename": filename,
        "document_id": document_id,
        "status": "processing",
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
                SELECT filename, id, uploaded_at, status, error_message, chunk_count
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
        {
            "filename": filename,
            "document_id": document_id,
            "timestamp": uploaded_at,
            "status": status,
            "error_message": error_message,
            "chunk_count": chunk_count,
        }
        for filename, document_id, uploaded_at, status, error_message, chunk_count in rows
    ]


@router.get("/documents/{document_id}")
def document_detail(
    document_id: int,
    username: str = Depends(get_current_user),
    organization: OrganizationContext = Depends(get_current_org),
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT filename, id, uploaded_at, status, error_message, chunk_count, processed_at
                FROM documents
                WHERE id = %s AND org_id = %s
                """,
                (document_id, organization.org_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    filename, document_id, uploaded_at, current_status, error_message, chunk_count, processed_at = row
    return {
        "filename": filename,
        "document_id": document_id,
        "timestamp": uploaded_at,
        "status": current_status,
        "error_message": error_message,
        "chunk_count": chunk_count,
        "processed_at": processed_at,
    }
