from pathlib import Path

from pgvector import Vector

from db.connection import get_db_connection

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def _apply_schema(cur):
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            cur.execute(statement)


def save_document_and_chunks(filename: str, chunks: list[dict]) -> tuple[int, int]:
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                _apply_schema(cur)
                cur.execute(
                    "INSERT INTO documents (filename) VALUES (%s) RETURNING id",
                    (filename,),
                )
                document_id = cur.fetchone()[0]

                for chunk in chunks:
                    cur.execute(
                        """
                        INSERT INTO chunks (document_id, text, page_number, chunk_index, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            chunk["text"],
                            chunk["page_number"],
                            chunk["chunk_index"],
                            Vector(chunk["embedding"].tolist()),
                        ),
                    )

                cur.execute(
                    "SELECT COUNT(*) FROM chunks WHERE document_id = %s",
                    (document_id,),
                )
                stored = cur.fetchone()[0]
        return document_id, stored
    finally:
        conn.close()
