import os

import psycopg2
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ORG_NAME = "Test Organization"
INVITE_CODE = "test-invite-code"
USERNAME = "testuser"
PASSWORD = "testpass123"


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO organizations (name, invite_code)
                VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET invite_code = EXCLUDED.invite_code
                RETURNING id
                """,
                (ORG_NAME, INVITE_CODE),
            )
            org_id = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO users (username, password_hash, org_id, role)
                VALUES (%s, %s, %s, 'admin')
                ON CONFLICT (username) DO UPDATE
                SET org_id = EXCLUDED.org_id, role = 'admin'
                """,
                (USERNAME, pwd_context.hash(PASSWORD), org_id),
            )

    print(f"Seeded organization '{ORG_NAME}' and admin user '{USERNAME}'.")
    print(f"Invite code: {INVITE_CODE}")


if __name__ == "__main__":
    main()