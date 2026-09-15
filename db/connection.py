import os

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

load_dotenv()


class DatabaseError(Exception):
    """Raised when Postgres is unreachable or a query fails."""


def get_db_connection():
    """Open a psycopg2 connection with the pgvector type registered."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise DatabaseError("DATABASE_URL is not set. Copy .env.example to .env and try again.")
    try:
        conn = psycopg2.connect(database_url)
    except psycopg2.Error as exc:
        raise DatabaseError(
            "Could not connect to Postgres. Start it with: docker compose up -d"
        ) from exc
    register_vector(conn)
    return conn
