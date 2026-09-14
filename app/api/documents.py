from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.security import get_current_user
from app.services.chunker import chunk_pages
from app.services.document_store import save_document_and_chunks
from app.services.embedder import embed_chunks
from app.services.pdf_parser import extract_text_from_pdf

router = APIRouter()

UPLOAD_DIR = Path("uploaded_docs")
documents = []


@router.post("/documents")
async def upload_document(file: UploadFile, username: str = Depends(get_current_user)):
    UPLOAD_DIR.mkdir(exist_ok=True)

    filename = Path(file.filename or "unnamed").name
    saved_path = UPLOAD_DIR / filename
    contents = await file.read()
    saved_path.write_bytes(contents)

    record = {
        "filename": filename,
        "path": str(saved_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    documents.append(record)

    pages, near_empty = extract_text_from_pdf(saved_path)
    chunks = [] if near_empty else chunk_pages(pages)

    if near_empty or not chunks:
        try:
            document_id, stored = save_document_and_chunks(filename, [])
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not connect to Postgres. Start it with: docker compose up -d",
            )
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
    try:
        document_id, stored = save_document_and_chunks(filename, chunks)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Postgres. Start it with: docker compose up -d",
        )

    return {
        "filename": filename,
        "document_id": document_id,
        "total_chunks_created": stored,
    }


@router.get("/documents")
def list_documents(username: str = Depends(get_current_user)):
    return documents
