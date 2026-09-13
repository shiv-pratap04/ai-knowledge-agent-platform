import os
import sys

import psycopg2
from dotenv import load_dotenv
from pgvector import Vector
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
QUERY = "My kitten is sleeping on the couch."


def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not set. Copy .env.example to .env and try again.")
        sys.exit(1)

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)
    query_embedding = model.encode(QUERY)

    print("Connecting to Postgres...")
    try:
        conn = psycopg2.connect(database_url)
    except psycopg2.OperationalError:
        print("Error: Could not connect to Postgres.")
        print("Make sure Docker is running and start the database with: docker compose up -d")
        sys.exit(1)

    register_vector(conn)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM test_embeddings")
        row_count = cur.fetchone()[0]
        if row_count == 0:
            print("Error: test_embeddings is empty.")
            print("Run day5_pgvector_test.py first to populate the table.")
            sys.exit(1)

        cur.execute(
            """
            SELECT sentence, embedding <=> %s AS distance
            FROM test_embeddings
            ORDER BY distance
            LIMIT 2
            """,
            (Vector(query_embedding.tolist()),),
        )
        results = cur.fetchall()

    conn.close()

    print(f"\nQuery: {QUERY}\n")
    print("Top 2 matches:\n")
    for rank, (sentence, distance) in enumerate(results, start=1):
        print(f"Match {rank}: {sentence}")
        print(f"Distance: {distance:.4f}\n")


if __name__ == "__main__":
    main()
