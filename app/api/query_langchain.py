import logging

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from app.api.query import build_sources
from app.core.security import get_current_user
from app.services.langchain_retriever import PgChunksRetriever
from db.connection import DatabaseError

logger = logging.getLogger(__name__)

router = APIRouter()

retriever = PgChunksRetriever(k=5)

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


def format_docs_as_context(docs) -> str:
    return "\n".join(
        f"[Page {doc.metadata.get('page_number')}]: {doc.page_content}" for doc in docs
    )


@router.post("/query-langchain")
def query_langchain(body: QueryRequest, username: str = Depends(get_current_user)):
    """Same RAG loop as /query, using a LangChain retriever + LCEL generation chain."""
    logger.info("LangChain query from %s: %s", username, body.question)
    try:
        docs = retriever.invoke(body.question)
    except DatabaseError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Postgres. Start it with: docker compose up -d",
        )
    except Exception:
        logger.exception("LangChain retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model failed to load or encode text. Check the server logs.",
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
        return {
            "question": body.question,
            "answer": "No relevant information found in the documents.",
            "sources": [],
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
    return {"question": body.question, "answer": answer.strip(), "sources": sources}
