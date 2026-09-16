import os
import sys

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import psycopg2
from pgvector.psycopg2 import register_vector

MODEL_NAME = "models/text-embedding-004"
EMBEDDING_DIM = 768

SENTENCES = [
    "The cat sat on the mat.",
    "A feline rested on the rug.",
    "The stock market crashed today.",
    "Investors panicked as prices fell.",
]


def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not set. Copy .env.example to .env and try again.")
        sys.exit(1)

    print("Loading embedding model...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model=MODEL_NAME,
        google_api_key=os.environ["GOOGLE_API_KEY"],
    ).embed_documents(SENTENCES)

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
            print("Enabling pgvector extension and creating table...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS test_embeddings (
                    id serial PRIMARY KEY,
                    sentence text,
                    embedding vector({EMBEDDING_DIM})
                )
                """
            )

            print("Clearing existing rows...")
            cur.execute("DELETE FROM test_embeddings")

            print("Inserting sentences and embeddings...")
            for sentence, embedding in zip(SENTENCES, embeddings):
                cur.execute(
                    "INSERT INTO test_embeddings (sentence, embedding) VALUES (%s, %s)",
                    (sentence, embedding),
                )

            print("\nFetching stored rows:\n")
            cur.execute("SELECT sentence, embedding FROM test_embeddings ORDER BY id")
            for sentence, embedding in cur.fetchall():
                print(f"Sentence: {sentence}")
                print(f"First 5 values: {embedding.to_list()[:5]}")
                print()

    conn.close()
    print("Done - embeddings round-tripped to Postgres successfully.")


if __name__ == "__main__":
    main()
