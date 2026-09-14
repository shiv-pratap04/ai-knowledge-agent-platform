from fastapi import APIRouter, Depends, HTTPException, status
from pgvector import Vector
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from app.core.security import get_current_user
from db.connection import get_db_connection

router = APIRouter()

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


class QueryRequest(BaseModel):
    question: str


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


@router.post("/query")
def query_chunks(body: QueryRequest, username: str = Depends(get_current_user)):
    model = get_embedding_model()
    query_embedding = model.encode(body.question)

    try:
        conn = get_db_connection()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Postgres. Start it with: docker compose up -d",
        )

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT text, page_number, chunk_index, document_id, embedding <=> %s AS distance
                FROM chunks
                ORDER BY distance
                LIMIT 5
                """,
                (Vector(query_embedding.tolist()),),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    matches = [
        {
            "text": text,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "document_id": document_id,
            "distance": float(distance),
        }
        for text, page_number, chunk_index, document_id, distance in rows
    ]

    return {"question": body.question, "matches": matches}
