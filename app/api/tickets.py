from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import OrganizationContext, get_current_org
from db.connection import DatabaseError
from app.services.ticket_service import create_ticket, get_ticket, list_tickets, update_ticket

router = APIRouter()


class TicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    category: str | None = None
    priority: str | None = None


class TicketUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    category: str | None = None
    priority: str | None = None
    status: str | None = None


@router.post("/tickets")
def create_ticket_endpoint(
    body: TicketCreateRequest,
    organization: OrganizationContext = Depends(get_current_org),
):
    try:
        return create_ticket(
            organization_id=organization.org_id,
            user_id=organization.user_id,
            title=body.title,
            description=body.description,
            category=body.category,
            priority=body.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create the support ticket.",
        ) from exc


@router.get("/tickets")
def list_ticket_endpoint(organization: OrganizationContext = Depends(get_current_org)):
    try:
        return list_tickets(organization.org_id)
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load support tickets.",
        ) from exc


@router.get("/tickets/{ticket_id}")
def ticket_detail(
    ticket_id: str,
    organization: OrganizationContext = Depends(get_current_org),
):
    try:
        return get_ticket(ticket_id, organization.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.") from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load support ticket.",
        ) from exc


@router.patch("/tickets/{ticket_id}")
def update_ticket_endpoint(
    ticket_id: str,
    body: TicketUpdateRequest,
    organization: OrganizationContext = Depends(get_current_org),
):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided to update.",
        )
    try:
        return update_ticket(ticket_id, organization.org_id, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.") from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update the support ticket.",
        ) from exc
