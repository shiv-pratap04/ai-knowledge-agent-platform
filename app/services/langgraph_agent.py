import json
import logging
import os

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - optional dependency in local dev/test environments
    ChatGoogleGenerativeAI = None

try:
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover
    def tool(func=None, *args, **kwargs):
        if func is None:
            return lambda wrapped: wrapped
        return func

try:
    from langgraph.prebuilt import create_react_agent
except ImportError:  # pragma: no cover
    create_react_agent = None

from app.services.langchain_retriever import PgChunksRetriever
from app.services.ticket_service import create_ticket

logger = logging.getLogger(__name__)


def create_support_ticket_tool(
    *,
    title: str,
    description: str,
    category: str = "IT_SUPPORT",
    priority: str = "MEDIUM",
    org_id: str,
    user_id: str,
) -> str:
    """Create an internal IT/support ticket for the authenticated organization."""
    if not org_id or not user_id:
        raise ValueError("Ticket creation requires an authenticated organization and user context.")

    ticket = create_ticket(
        organization_id=org_id,
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        priority=priority,
    )
    return (
        "Ticket created successfully.\n"
        f"Ticket ID: {ticket['ticket_id']}\n"
        f"Status: {ticket['status']}\n"
        f"Priority: {ticket['priority']}\n"
        f"Category: {ticket['category']}"
    )


def _build_agent(org_id: str, user_id: str):
    if ChatGoogleGenerativeAI is None or create_react_agent is None:
        raise RuntimeError("LangGraph or Google AI dependencies are not installed.")
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

    @tool
    def create_support_ticket(
        title: str,
        description: str,
        category: str = "IT_SUPPORT",
        priority: str = "MEDIUM",
    ) -> str:
        """Create an internal IT support ticket only when the user explicitly requests one or follow-up workflow requires it after checking docs."""
        try:
            return create_support_ticket_tool(
                title=title,
                description=description,
                category=category,
                priority=priority,
                org_id=org_id,
                user_id=user_id,
            )
        except ValueError as exc:
            return f"Ticket creation could not proceed: {exc}"

    return create_react_agent(
        model=ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            google_api_key=os.environ["GOOGLE_API_KEY"],
        ),
        tools=[search_knowledge_base, create_support_ticket],
        prompt=(
            "You are a knowledge-base and support agent. "
            "Use search_knowledge_base for questions about uploaded documents, policies, or troubleshooting guidance. "
            "Use create_support_ticket only when the user explicitly asks to create, raise, or open a ticket, or when a workflow clearly requires a ticket after checking knowledge-base guidance. "
            "Do not create a ticket merely because a user describes an issue without an explicit ticket request. "
            "If the user's request is missing important ticket details such as the issue description or a ticket title, ask for clarification before calling create_support_ticket. "
            "Answer using retrieved evidence and cite the source page when available. If no evidence is found, say you do not know."
        ),
    )


def invoke_agent(question: str, org_id: str, user_id: str):
    """Run the LangGraph agent and return its answer plus tool metadata."""
    logger.info("LangGraph agent started")
    result = _build_agent(org_id, user_id).invoke(
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
