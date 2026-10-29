import logging

import psycopg2

from app.services.cache import delete_conversation_cached
from db.connection import DatabaseError, get_db_connection

logger = logging.getLogger(__name__)

VALID_TICKET_CATEGORIES = {
    "IT_SUPPORT",
    "NETWORK",
    "HARDWARE",
    "SOFTWARE",
    "ACCESS",
    "ACCOUNT",
    "OTHER",
}
VALID_TICKET_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_TICKET_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}


def _normalize_enum(value: str | None, *, allowed: set[str], field_name: str, default: str | None = None) -> str:
    if value is None:
        if default is None:
            raise ValueError(f"{field_name} is required.")
        return default

    normalized = str(value).strip().upper()
    if normalized not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"Invalid {field_name}: {value}. Allowed values: {allowed_values}.")
    return normalized


def _validate_title(title: str) -> str:
    cleaned = (title or "").strip()
    if len(cleaned) < 3 or len(cleaned) > 200:
        raise ValueError("Title must be between 3 and 200 characters.")
    return cleaned


def _validate_description(description: str) -> str:
    cleaned = (description or "").strip()
    if len(cleaned) < 10 or len(cleaned) > 5000:
        raise ValueError("Description must be between 10 and 5000 characters.")
    return cleaned


def _serialize_ticket(row: tuple) -> dict:
    if not row:
        return {}

    if len(row) == 9:
        if str(row[0]).upper().startswith("TKT-"):
            ticket_id, title, description, category, priority, status, created_at, updated_at, organization_id = row
            created_by = None
            _id = None
        elif str(row[1]).upper().startswith("TKT-"):
            _id, ticket_id, title, description, category, priority, status, created_at, updated_at = row
            organization_id = None
            created_by = None
        else:
            ticket_id = row[0]
            title = row[1]
            description = row[2]
            category = row[3]
            priority = row[4]
            status = row[5]
            created_at = row[6]
            updated_at = row[7]
            organization_id = row[8]
            created_by = None
            _id = None
    else:
        (
            _id,
            ticket_id,
            organization_id,
            created_by,
            title,
            description,
            category,
            priority,
            status,
            created_at,
            updated_at,
        ) = row

    return {
        "id": str(_id) if _id is not None else None,
        "ticket_id": ticket_id,
        "organization_id": str(organization_id) if organization_id is not None else None,
        "created_by": str(created_by) if created_by is not None else None,
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def create_ticket(
    organization_id: str | None = None,
    user_id: str | None = None,
    title: str | None = None,
    description: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    **kwargs,
) -> dict:
    if organization_id is None:
        organization_id = kwargs.get("org_id")
    if user_id is None:
        user_id = kwargs.get("created_by") or kwargs.get("user")
    if title is None:
        title = kwargs.get("title")
    if description is None:
        description = kwargs.get("description")
    validated_title = _validate_title(title)
    validated_description = _validate_description(description)
    validated_category = _normalize_enum(
        category,
        allowed=VALID_TICKET_CATEGORIES,
        field_name="category",
        default="IT_SUPPORT",
    )
    validated_priority = _normalize_enum(
        priority,
        allowed=VALID_TICKET_PRIORITIES,
        field_name="priority",
        default="MEDIUM",
    )
    validated_status = _normalize_enum(
        status,
        allowed=VALID_TICKET_STATUSES,
        field_name="status",
        default="OPEN",
    )

    logger.info(
        "Ticket creation requested for org=%s user=%s category=%s priority=%s",
        organization_id,
        user_id,
        validated_category,
        validated_priority,
    )

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tickets (
                        organization_id,
                        created_by,
                        title,
                        description,
                        category,
                        priority,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, ticket_id, organization_id, created_by, title, description, category, priority, status, created_at, updated_at
                    """,
                    (
                        organization_id,
                        user_id,
                        validated_title,
                        validated_description,
                        validated_category,
                        validated_priority,
                        validated_status,
                    ),
                )
                row = cur.fetchone()
    except (psycopg2.Error, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise DatabaseError("Failed to create support ticket.") from exc
    finally:
        conn.close()

    ticket = _serialize_ticket(row)
    logger.info("Ticket created for org=%s: %s", organization_id, ticket.get("ticket_id"))
    return ticket


def list_tickets(organization_id: str) -> list[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ticket_id, organization_id, created_by, title, description, category, priority, status, created_at, updated_at
                FROM tickets
                WHERE organization_id = %s
                ORDER BY created_at DESC, ticket_id DESC
                """,
                (organization_id,),
            )
            rows = cur.fetchall()
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to list tickets.") from exc
    finally:
        conn.close()

    return [_serialize_ticket(row) for row in rows]


def get_ticket(ticket_id: str, organization_id: str) -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ticket_id, organization_id, created_by, title, description, category, priority, status, created_at, updated_at
                FROM tickets
                WHERE ticket_id = %s AND organization_id = %s
                """,
                (ticket_id, organization_id),
            )
            row = cur.fetchone()
    except psycopg2.Error as exc:
        raise DatabaseError("Failed to load ticket.") from exc
    finally:
        conn.close()

    if not row:
        raise ValueError("Ticket not found for this organization.")
    return _serialize_ticket(row)


def update_ticket(
    ticket_id: str,
    organization_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> dict:
    current = get_ticket(ticket_id, organization_id)
    updates = {
        "title": _validate_title(title) if title is not None else current["title"],
        "description": _validate_description(description) if description is not None else current["description"],
        "category": _normalize_enum(category, allowed=VALID_TICKET_CATEGORIES, field_name="category", default=current["category"]),
        "priority": _normalize_enum(priority, allowed=VALID_TICKET_PRIORITIES, field_name="priority", default=current["priority"]),
        "status": _normalize_enum(status, allowed=VALID_TICKET_STATUSES, field_name="status", default=current["status"]),
    }

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tickets
                    SET title = %s,
                        description = %s,
                        category = %s,
                        priority = %s,
                        status = %s,
                        updated_at = NOW()
                    WHERE ticket_id = %s AND organization_id = %s
                    RETURNING id, ticket_id, organization_id, created_by, title, description, category, priority, status, created_at, updated_at
                    """,
                    (
                        updates["title"],
                        updates["description"],
                        updates["category"],
                        updates["priority"],
                        updates["status"],
                        ticket_id,
                        organization_id,
                    ),
                )
                row = cur.fetchone()
    except (psycopg2.Error, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise DatabaseError("Failed to update ticket.") from exc
    finally:
        conn.close()

    if not row:
        raise ValueError("Ticket not found for this organization.")
    return _serialize_ticket(row)
