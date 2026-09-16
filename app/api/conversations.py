from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import OrganizationContext, get_current_org
from app.services.cache import conversation_cache_key, get_cached, set_cached
from app.services.conversation_store import (
    create_conversation,
    get_conversation,
    list_conversations,
)
from db.connection import DatabaseError

router = APIRouter()


class ConversationCreateRequest(BaseModel):
    title: str = "New conversation"


def _handle_store_error(exc: DatabaseError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not access conversation storage.",
    )


@router.get("/conversations")
def conversations(organization: OrganizationContext = Depends(get_current_org)):
    try:
        return list_conversations(organization.org_id, organization.user_id)
    except DatabaseError as exc:
        raise _handle_store_error(exc) from exc


@router.get("/conversations/{conversation_id}")
def conversation_detail(
    conversation_id: str,
    organization: OrganizationContext = Depends(get_current_org),
):
    cache_key = conversation_cache_key(
        organization.org_id,
        organization.user_id,
        conversation_id,
    )
    cached = get_cached(cache_key)
    if cached:
        return cached
    try:
        conversation = get_conversation(
            conversation_id,
            organization.org_id,
            organization.user_id,
        )
        set_cached(cache_key, conversation)
        return conversation
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.") from exc
    except DatabaseError as exc:
        raise _handle_store_error(exc) from exc


@router.post("/conversations")
def create_empty_conversation(
    body: ConversationCreateRequest,
    organization: OrganizationContext = Depends(get_current_org),
):
    try:
        conversation_id = create_conversation(
            organization.org_id,
            organization.user_id,
            body.title,
        )
    except DatabaseError as exc:
        raise _handle_store_error(exc) from exc
    return {"id": conversation_id, "title": body.title[:200]}