import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import OrganizationContext, get_current_org, get_current_user
from app.services.conversation_store import add_message, get_or_create_conversation
from app.services.langgraph_agent import invoke_agent
from db.connection import DatabaseConnectionError, DatabaseError, DatabaseQueryError

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentRequest(BaseModel):
    question: str
    conversation_id: str | None = None


@router.post("/agent")
def run_agent(
    body: AgentRequest,
    username: str = Depends(get_current_user),
    organization: OrganizationContext = Depends(get_current_org),
):
    """Run the LangGraph knowledge-base agent."""
    logger.info("LangGraph agent request from %s", username)
    try:
        conversation_id = get_or_create_conversation(
            body.conversation_id,
            organization.org_id,
            organization.user_id,
            body.question,
        )
        add_message(conversation_id, "user", body.question)
        result = invoke_agent(body.question, organization.org_id)
    except DatabaseConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Postgres. Start it with: docker compose up -d",
        )
    except DatabaseQueryError:
        logger.exception("LangGraph retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge-base retrieval failed. Check the server logs.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist the conversation.",
        ) from exc
    except Exception:
        logger.exception("LangGraph agent failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LangGraph agent is unavailable. Check Ollama and server logs.",
        )

    add_message(
        conversation_id,
        "assistant",
        result["content"],
        citations=result["citations"],
        tool_calls=result["tool_calls"],
    )
    return {
        "question": body.question,
        "answer": result["content"],
        "conversation_id": conversation_id,
    }
