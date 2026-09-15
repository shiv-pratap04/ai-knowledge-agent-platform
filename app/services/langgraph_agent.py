import json
import logging

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from app.services.langchain_retriever import PgChunksRetriever

logger = logging.getLogger(__name__)

_retriever = PgChunksRetriever(k=5)


@tool
def search_knowledge_base(question: str) -> str:
    """Search indexed PDF chunks for information relevant to a question."""
    documents = _retriever.invoke(question)
    if not documents:
        return "No relevant information was found in the indexed documents."

    return "\n\n".join(
        json.dumps(
            {
                "page": document.metadata.get("page_number"),
                "filename": document.metadata.get("filename"),
                "text": document.page_content,
            }
        )
        for document in documents
    )


_agent = create_react_agent(
    model=ChatOllama(model="llama3.2"),
    tools=[search_knowledge_base],
    prompt=(
        "You are a knowledge-base agent. Use search_knowledge_base for questions "
        "about uploaded documents. Answer only from retrieved evidence and cite "
        "the source page when available. If no evidence is found, say you do not know."
    ),
)


def invoke_agent(question: str):
    """Run the LangGraph agent and return its final message."""
    logger.info("LangGraph agent started")
    result = _agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    logger.info("LangGraph agent completed")
    return result["messages"][-1]
