from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile

from app.core.security import get_current_user

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

    return {
        "filename": filename,
        "saved": True,
        "path": record["path"],
    }


@router.get("/documents")
def list_documents(username: str = Depends(get_current_user)):
    return documents
