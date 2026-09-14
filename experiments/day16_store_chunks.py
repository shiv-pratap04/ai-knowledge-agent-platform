import os
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pgvector import Vector
from pgvector.psycopg2 import register_vector
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = ROOT / "uploaded_docs"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
CHUNK_SIZE = 500
OVERLAP = 50
MODEL_NAME = "all-MiniLM-L6-v2"


def find_pdf():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])

    pdfs = sorted(UPLOAD_DIR.glob("*.pdf"))
    if pdfs:
        return pdfs[0]

    print("Error: no PDF found.")
    print("Upload a PDF via POST /documents, put one in uploaded_docs/, or pass a path:")
    print("  python experiments/day16_store_chunks.py path/to/file.pdf")
    sys.exit(1)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    if not text.strip():
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def extract_chunks(pdf_path):
    reader = PdfReader(str(pdf_path))
    chunks = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for chunk_index, chunk in enumerate(
            chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
        ):
            chunks.append(
                {
                    "text": chunk,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                }
            )
    return chunks


def apply_schema(cur):
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            cur.execute(statement)


def main():
    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not set. Copy .env.example to .env and try again.")
        sys.exit(1)

    pdf_path = find_pdf()
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}")
        sys.exit(1)

    print(f"Opening: {pdf_path}")
    chunks = extract_chunks(pdf_path)
    print(f"Chunks extracted: {len(chunks)}")
    if not chunks:
        print("No text chunks found. Try a PDF with selectable text.")
        sys.exit(1)

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    started = time.perf_counter()
    embeddings = model.encode([item["text"] for item in chunks])
    elapsed = time.perf_counter() - started
    print(f"Embedded {len(chunks)} chunks in {elapsed:.2f} seconds")

    print("Connecting to Postgres...")
    try:
        conn = psycopg2.connect(database_url)
    except psycopg2.OperationalError:
        print("Error: Could not connect to Postgres.")
        print("Make sure Docker is running and start the database with: docker compose up -d")
        sys.exit(1)

    register_vector(conn)

    with conn:
        with conn.cursor() as cur:
            print(f"Applying schema from {SCHEMA_PATH}...")
            apply_schema(cur)

            cur.execute(
                "INSERT INTO documents (filename) VALUES (%s) RETURNING id",
                (pdf_path.name,),
            )
            document_id = cur.fetchone()[0]
            print(f"Inserted document id={document_id} filename={pdf_path.name}")

            print("Inserting chunks...")
            for item, embedding in zip(chunks, embeddings):
                cur.execute(
                    """
                    INSERT INTO chunks (document_id, text, page_number, chunk_index, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        document_id,
                        item["text"],
                        item["page_number"],
                        item["chunk_index"],
                        Vector(embedding.tolist()),
                    ),
                )

            cur.execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id = %s",
                (document_id,),
            )
            stored = cur.fetchone()[0]
            print(f"Stored chunks for document {document_id}: {stored}")

    conn.close()
    print("Done - chunks are now in Postgres.")


if __name__ == "__main__":
    main()
