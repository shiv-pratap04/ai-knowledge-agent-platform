import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.langgraph_agent import invoke_agent
from db.connection import DatabaseConnectionError, DatabaseQueryError

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentRequest(BaseModel):
    question: str


@router.post("/agent")
def run_agent(body: AgentRequest, username: str = Depends(get_current_user)):
    """Run the LangGraph knowledge-base agent."""
    logger.info("LangGraph agent request from %s", username)
    try:
        message = invoke_agent(body.question)
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
    except Exception:
        logger.exception("LangGraph agent failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LangGraph agent is unavailable. Check Ollama and server logs.",
        )

    return {"question": body.question, "answer": message.content}
