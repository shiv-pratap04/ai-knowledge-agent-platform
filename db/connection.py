import os
import logging

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when Postgres is unreachable or a query fails."""


class DatabaseConnectionError(DatabaseError):
    """Raised when a Postgres connection cannot be established."""


class DatabaseQueryError(DatabaseError):
    """Raised when a Postgres query or pgvector setup fails."""


def get_db_connection():
    """Open a psycopg2 connection with the pgvector type registered."""
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")
    if not database_url:
        raise DatabaseConnectionError(
            "DATABASE_URL is not set. Copy .env.example to .env and try again."
        )
    try:
        conn = psycopg2.connect(database_url)
    except psycopg2.Error as exc:
        raise DatabaseConnectionError(
            "Could not connect to Postgres. Start it with: docker compose up -d"
        ) from exc
    try:
        register_vector(conn)
    except psycopg2.Error as exc:
        conn.close()
        raise DatabaseQueryError("Could not register the pgvector type.") from exc
    logger.info("Connected to Postgres")
    return conn
