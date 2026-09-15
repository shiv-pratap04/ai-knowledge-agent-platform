from fastapi import APIRouter, Depends

from app.core.security import OrganizationContext, require_admin
from db.connection import get_db_connection

router = APIRouter()


@router.get("/org/members")
def list_org_members(
    organization: OrganizationContext = Depends(require_admin),
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, role, created_at
                FROM users
                WHERE org_id = %s
                ORDER BY created_at
                """,
                (organization.org_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "user_id": str(user_id),
            "username": username,
            "role": role,
            "created_at": created_at,
        }
        for user_id, username, role, created_at in rows
    ]


@router.get("/org/usage")
def org_usage(organization: OrganizationContext = Depends(require_admin)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM documents WHERE org_id = %s",
                (organization.org_id,),
            )
            document_count = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*)
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.org_id = %s AND m.role = 'user'
                """,
                (organization.org_id,),
            )
            query_count = cur.fetchone()[0]
    finally:
        conn.close()

    return {"org_id": organization.org_id, "document_count": document_count, "query_count": query_count}