import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pgvector import Vector
from pydantic import BaseModel
from app.core.security import get_current_user
from app.services.embedder import get_embedding_model
from db.connection import get_db_connection

router = APIRouter()

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"


class QueryRequest(BaseModel):
    question: str


def retrieve_chunks(question: str):
    model = get_embedding_model()
    query_embedding = model.encode(question)

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
                SELECT c.text, c.page_number, c.chunk_index, c.document_id,
                       d.filename, c.embedding <=> %s AS distance
                FROM chunks c
                LEFT JOIN documents d ON d.id = c.document_id
                ORDER BY distance
                LIMIT 5
                """,
                (Vector(query_embedding.tolist()),),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "text": text,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "document_id": document_id,
            "filename": filename or f"document-{document_id}",
            "distance": float(distance),
        }
        for text, page_number, chunk_index, document_id, filename, distance in rows
    ]


def build_sources(chunks):
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk["document_id"], chunk["page_number"])
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "filename": chunk["filename"],
                "page_number": chunk["page_number"],
            }
        )
    return sources


def build_context(chunks):
    return "\n".join(
        f"[Page {chunk['page_number']}]: {chunk['text']}" for chunk in chunks
    )


def ask_ollama(question: str, context: str) -> str:
    system_prompt = (
        "You are a helpful assistant. Answer the user's question using ONLY "
        "the provided context below. If the answer isn't in the context, say "
        "you don't know. When referencing information, mention which page it "
        "came from if useful, using the format (Page X). "
        f"Context:\n{context}"
    )
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "system": system_prompt,
                "prompt": question,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Ollama at http://localhost:11434. Start Ollama and try again.",
        )
    except requests.exceptions.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ollama returned {exc.response.status_code}",
        )
    return response.json()["response"].strip()


@router.post("/query")
def query_chunks(body: QueryRequest, username: str = Depends(get_current_user)):
    matches = retrieve_chunks(body.question)
    sources = build_sources(matches)

    if not matches:
        return {
            "question": body.question,
            "answer": "No relevant information found in the documents.",
            "sources": [],
        }

    context = build_context(matches)
    answer = ask_ollama(body.question, context)
    return {"question": body.question, "answer": answer, "sources": sources}
