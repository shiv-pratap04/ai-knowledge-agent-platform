from datetime import datetime, timezone
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


def create_document(filename: str, storage_path: str, org_id: str) -> int:
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (filename, storage_path, org_id, status)
                    VALUES (%s, %s, %s, 'processing')
                    RETURNING id
                    """,
                    (filename, storage_path, org_id),
                )
                return cur.fetchone()[0]
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to create document record.") from exc
    finally:
        conn.close()


def get_document_for_processing(document_id: int) -> dict | None:
    """Claim a document under an advisory lock for the task's processing window."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (document_id,))
            if not cur.fetchone()[0]:
                conn.close()
                return None
            cur.execute(
                """
                SELECT storage_path, status
                FROM documents
                WHERE id = %s
                FOR UPDATE
                """,
                (document_id,),
            )
            row = cur.fetchone()
            if not row or row[1] != "processing":
                conn.close()
                return None
                conn.commit()
                return {"storage_path": row[0], "connection": conn}
    except psycopg2.Error as exc:
        conn.close()
        raise DatabaseError("Failed to claim document for processing.") from exc


def release_document_processing(document: dict) -> None:
    document["connection"].close()


def save_chunks_for_document(document_id: int, chunks: list[dict]) -> int:
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
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
                return len(chunks)
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to save document chunks.") from exc
    finally:
        conn.close()


def mark_document_ready(document_id: int, chunk_count: int) -> None:
    _update_document_status(document_id, "ready", chunk_count=chunk_count)


def mark_document_failed(document_id: int, error_message: str) -> None:
    _update_document_status(document_id, "failed", error_message=error_message[:2000])


def _update_document_status(
    document_id: int,
    status: str,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE documents
                    SET status = %s,
                        chunk_count = COALESCE(%s, chunk_count),
                        error_message = %s,
                        processed_at = CASE WHEN %s = 'ready' THEN %s ELSE processed_at END,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        status,
                        chunk_count,
                        error_message,
                        status,
                        datetime.now(timezone.utc),
                        document_id,
                    ),
                )
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to update document status.") from exc
    finally:
        conn.close()
