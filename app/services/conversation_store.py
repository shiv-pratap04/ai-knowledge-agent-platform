import json
from uuid import UUID

import psycopg2

from db.connection import DatabaseError, get_db_connection


def get_or_create_conversation(
    conversation_id: str | None,
    org_id: str,
    user_id: str,
    title: str,
) -> str:
    """Return an organization-owned conversation or create one for the user."""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                if conversation_id:
                    UUID(conversation_id)
                    cur.execute(
                        """
                        SELECT id
                        FROM conversations
                        WHERE id = %s AND org_id = %s AND user_id = %s
                        """,
                        (conversation_id, org_id, user_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise ValueError("Conversation not found for this user and organization.")
                    return str(row[0])

                cur.execute(
                    """
                    INSERT INTO conversations (org_id, user_id, title)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (org_id, user_id, title[:200]),
                )
                return str(cur.fetchone()[0])
    except ValueError:
        raise
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to create or load conversation.") from exc
    finally:
        conn.close()


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    citations=None,
    tool_calls=None,
) -> None:
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (conversation_id, role, content, citations, tool_calls)
                    VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)
                    """,
                    (
                        conversation_id,
                        role,
                        content,
                        json.dumps(citations) if citations is not None else None,
                        json.dumps(tool_calls) if tool_calls is not None else None,
                    ),
                )
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to store conversation message.") from exc
    finally:
        conn.close()