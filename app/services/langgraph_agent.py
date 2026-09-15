import json
import logging

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from app.services.langchain_retriever import PgChunksRetriever

logger = logging.getLogger(__name__)


def _build_agent(org_id: str):
    retriever = PgChunksRetriever(k=5, org_id=org_id)

    @tool
    def search_knowledge_base(question: str) -> str:
        """Search indexed PDF chunks for information relevant to a question."""
        documents = retriever.invoke(question)
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

    return create_react_agent(
        model=ChatOllama(model="llama3.2"),
        tools=[search_knowledge_base],
        prompt=(
            "You are a knowledge-base agent. Use search_knowledge_base for questions "
            "about uploaded documents. Answer only from retrieved evidence and cite "
            "the source page when available. If no evidence is found, say you do not know."
        ),
    )


def invoke_agent(question: str, org_id: str):
    """Run the LangGraph agent and return its answer plus tool metadata."""
    logger.info("LangGraph agent started")
    result = _build_agent(org_id).invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    logger.info("LangGraph agent completed")
    tool_calls = []
    citations = []
    for message in result["messages"]:
        tool_calls.extend(getattr(message, "tool_calls", None) or [])
        if getattr(message, "type", None) != "tool":
            continue
        for item in str(message.content).split("\n\n"):
            try:
                citation = json.loads(item)
            except json.JSONDecodeError:
                continue
            citations.append(
                {
                    "filename": citation.get("filename"),
                    "page_number": citation.get("page"),
                }
            )

    final_message = result["messages"][-1]
    return {
        "content": final_message.content,
        "citations": citations or None,
        "tool_calls": tool_calls or None,
    }
