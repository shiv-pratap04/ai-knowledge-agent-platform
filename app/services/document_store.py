import logging
from pathlib import Path

import psycopg2
from pgvector import Vector

from db.connection import DatabaseError, get_db_connection

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def _apply_schema(cur):
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    cur.execute(sql)


def save_document_and_chunks(
    filename: str, chunks: list[dict], org_id: str
) -> tuple[int, int]:
    """Insert a documents row and its chunks. Returns (document_id, chunk_count)."""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                _apply_schema(cur)
                cur.execute(
                    """
                    INSERT INTO documents (filename, org_id)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (filename, org_id),
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
                            Vector(
                                chunk["embedding"].tolist()
                                if hasattr(chunk["embedding"], "tolist")
                                else chunk["embedding"]
                            ),
                        ),
                    )

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE c.document_id = %s AND d.org_id = %s
                    """,
                    (document_id, org_id),
                )
                stored = cur.fetchone()[0]
        logger.info("Stored document id=%s filename=%s chunks=%s", document_id, filename, stored)
        return document_id, stored
    except (psycopg2.Error, OSError) as exc:
        raise DatabaseError("Failed to save document and chunks to Postgres.") from exc
    finally:
        conn.close()
