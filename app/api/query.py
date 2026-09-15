import logging

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from app.core.security import OrganizationContext, get_current_org, get_current_user
from app.services.conversation_store import add_message, get_or_create_conversation
from app.services.langchain_retriever import PgChunksRetriever
from db.connection import DatabaseConnectionError, DatabaseError, DatabaseQueryError

logger = logging.getLogger(__name__)

router = APIRouter()

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant. Answer the user's question using ONLY "
            "the provided context below. If the answer isn't in the context, say "
            "you don't know. When referencing information, mention which page it "
            "came from if useful, using the format (Page X).\n"
            "Context:\n{context}",
        ),
        ("human", "{question}"),
    ]
)

# Generation half of LCEL. Retriever is invoked separately so we can return
# sources without embedding/querying twice.
chain = prompt | ChatOllama(model="llama3.2") | StrOutputParser()


class QueryRequest(BaseModel):
    question: str
    conversation_id: str | None = None


def build_sources(matches):
    """Deduplicate citations by document and page."""
    seen = set()
    sources = []
    for match in matches:
        key = (match["document_id"], match["page_number"])
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "filename": match["filename"],
                "page_number": match["page_number"],
            }
        )
    return sources


def format_docs_as_context(docs) -> str:
    return "\n".join(
        f"[Page {doc.metadata.get('page_number')}]: {doc.page_content}" for doc in docs
    )


@router.post("/query")
def query(
    body: QueryRequest,
    username: str = Depends(get_current_user),
    organization: OrganizationContext = Depends(get_current_org),
):
    """Retrieve and answer using the canonical LangChain RAG chain."""
    logger.info("LangChain query from %s: %s", username, body.question)
    try:
        conversation_id = get_or_create_conversation(
            body.conversation_id,
            organization.org_id,
            organization.user_id,
            body.question,
        )
        add_message(conversation_id, "user", body.question)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist the conversation.",
        ) from exc

    try:
        docs = PgChunksRetriever(k=5, org_id=organization.org_id).invoke(body.question)
    except DatabaseConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Postgres. Start it with: docker compose up -d",
        )
    except DatabaseQueryError:
        logger.exception("LangChain vector retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vector retrieval failed. Check the server logs.",
        )
    except Exception:
        logger.exception("LangChain retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LangChain retrieval failed. Check the server logs.",
        )

    matches = [
        {
            "filename": doc.metadata["filename"],
            "document_id": doc.metadata["document_id"],
            "page_number": doc.metadata["page_number"],
        }
        for doc in docs
    ]
    sources = build_sources(matches)

    if not docs:
        answer = "No relevant information found in the documents."
        add_message(conversation_id, "assistant", answer, citations=[])
        return {
            "question": body.question,
            "answer": answer,
            "sources": [],
            "conversation_id": conversation_id,
        }

    context = format_docs_as_context(docs)
    try:
        answer = chain.invoke({"context": context, "question": body.question})
    except Exception:
        logger.exception("Ollama/LangChain generation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Ollama at http://localhost:11434. Start Ollama and try again.",
        )

    logger.info("LangChain answer returned (%s chars, %s sources)", len(answer), len(sources))
    answer = answer.strip()
    add_message(conversation_id, "assistant", answer, citations=sources)
    return {
        "question": body.question,
        "answer": answer,
        "sources": sources,
        "conversation_id": conversation_id,
    }
