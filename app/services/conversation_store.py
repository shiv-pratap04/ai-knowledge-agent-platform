import json
from uuid import UUID

import psycopg2

from app.services.cache import delete_conversation_cached
from db.connection import DatabaseError, get_db_connection


def create_conversation(org_id: str, user_id: str, title: str) -> str:
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversations (org_id, user_id, title)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (org_id, user_id, title[:200]),
                )
                return str(cur.fetchone()[0])
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to create conversation.") from exc
    finally:
        conn.close()


def list_conversations(org_id: str, user_id: str) -> list[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.title, c.created_at,
                       (
                           SELECT m.content
                           FROM messages m
                           WHERE m.conversation_id = c.id
                           ORDER BY m.created_at DESC, m.id DESC
                           LIMIT 1
                       ) AS last_message_preview
                FROM conversations c
                WHERE c.org_id = %s AND c.user_id = %s
                ORDER BY c.created_at DESC
                """,
                (org_id, user_id),
            )
            rows = cur.fetchall()
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to list conversations.") from exc
    finally:
        conn.close()

    return [
        {
            "id": str(conversation_id),
            "title": title,
            "created_at": created_at,
            "last_message_preview": preview,
        }
        for conversation_id, title, created_at, preview in rows
    ]


def get_conversation(conversation_id: str, org_id: str, user_id: str) -> dict:
    UUID(conversation_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, created_at
                FROM conversations
                WHERE id = %s AND org_id = %s AND user_id = %s
                """,
                (conversation_id, org_id, user_id),
            )
            conversation = cur.fetchone()
            if not conversation:
                raise ValueError("Conversation not found.")

            cur.execute(
                """
                SELECT id, role, content, citations, tool_calls, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at, id
                """,
                (conversation_id,),
            )
            messages = cur.fetchall()
    except ValueError:
        raise
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to load conversation.") from exc
    finally:
        conn.close()

    return {
        "id": str(conversation[0]),
        "title": conversation[1],
        "created_at": conversation[2],
        "messages": [
            {
                "id": str(message_id),
                "role": role,
                "content": content,
                "citations": citations,
                "tool_calls": tool_calls,
                "created_at": created_at,
            }
            for message_id, role, content, citations, tool_calls, created_at in messages
        ],
    }


def get_or_create_conversation(
    conversation_id: str | None,
    org_id: str,
    user_id: str,
    title: str,
) -> str:
    """Return an organization-owned conversation or create one for the user."""
    if not conversation_id:
        return create_conversation(org_id, user_id, title)

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
    delete_conversation_cached(conversation_id)
