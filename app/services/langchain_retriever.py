"""LangChain retriever over the existing pgvector `chunks` table.

langchain-postgres PGVector expects its own collection/metadata schema.
Our table already has document_id, page_number, chunk_index, so we wrap
the same cosine-distance SQL used by POST /query.
"""

import psycopg2
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from pgvector import Vector

from db.connection import DatabaseError, get_db_connection

_embeddings = None


def get_query_embeddings() -> HuggingFaceEmbeddings:
    """Same MiniLM wrapper as experiments/langchain_basics/embeddings.py."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings


class PgChunksRetriever(BaseRetriever):
    """Top-k cosine search against the existing `chunks` table."""

    k: int = 5
    org_id: str

    def _get_relevant_documents(self, query: str) -> list[Document]:
        vector = get_query_embeddings().embed_query(query)
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.text, c.page_number, c.chunk_index, c.document_id,
                           d.filename, c.embedding <=> %s AS distance
                    FROM chunks c
                    LEFT JOIN documents d ON d.id = c.document_id
                        WHERE d.org_id = %s AND d.status = 'ready'
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (Vector(vector), self.org_id, self.k),
                )
                rows = cur.fetchall()
        except psycopg2.Error as exc:
            raise DatabaseError("Failed to search chunks in Postgres.") from exc
        finally:
            conn.close()

        return [
            Document(
                page_content=text,
                metadata={
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "document_id": document_id,
                    "filename": filename or f"document-{document_id}",
                    "distance": float(distance),
                },
            )
            for text, page_number, chunk_index, document_id, filename, distance in rows
        ]
