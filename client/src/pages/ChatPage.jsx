import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";
import {
  createConversation,
  getConversation,
  listConversations,
  sendAgentMessage,
} from "../api";

function formatDate(value) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(value));
}

function makeOptimisticMessage(role, content) {
  return { id: `pending-${Date.now()}`, role, content, citations: [] };
}

export function ChatPage() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [citation, setCitation] = useState(null);
  const messagesEndRef = useRef(null);

  const refreshConversations = useCallback(async () => {
    setLoading(true);
    try {
      setConversations(await listConversations(token));
    } catch (requestError) {
      setError(requestError.message);
      showToast(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { refreshConversations(); }, [refreshConversations]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [activeConversation?.messages, sending]);

  async function openConversation(id) {
    setError("");
    try {
      setActiveConversation(await getConversation(token, id));
    } catch (requestError) {
      setError(requestError.message);
      showToast(requestError.message);
    }
  }

  async function startConversation() {
    setError("");
    try {
      const conversation = await createConversation(token);
      setConversations((current) => [{ ...conversation, created_at: new Date().toISOString() }, ...current]);
      setActiveConversation({ ...conversation, messages: [], created_at: new Date().toISOString() });
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function sendMessage(event) {
    event?.preventDefault();
    const question = draft.trim();
    if (!question || sending) return;

    const optimistic = makeOptimisticMessage("user", question);
    const previous = activeConversation;
    setDraft("");
    setError("");
    setSending(true);
    setActiveConversation((current) => ({
      ...(current || { id: null, title: question, messages: [] }),
      title: current?.title || question,
      messages: [...(current?.messages || []), optimistic],
    }));

    try {
      const response = await sendAgentMessage(token, question, previous?.id);
      const fullConversation = await getConversation(token, response.conversation_id);
      setActiveConversation(fullConversation);
      await refreshConversations();
    } catch (requestError) {
      setDraft(question);
      setError(requestError.message);
      showToast(requestError.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-page">
      <aside className="conversation-sidebar">
        <div className="conversation-heading">
          <div><p className="eyebrow">Agent workspace</p><h2>Conversations</h2></div>
          <button className="new-conversation-button" onClick={startConversation} title="New conversation">+</button>
        </div>
        <button className="new-thread-button" onClick={startConversation}>＋ New conversation</button>
        <div className="conversation-list">
          {loading ? <p className="sidebar-empty">Loading threads...</p> : conversations.length === 0 ? <p className="sidebar-empty">Your threads will appear here.</p> : conversations.map((item) => <button className={`conversation-item ${activeConversation?.id === item.id ? "active" : ""}`} key={item.id} onClick={() => openConversation(item.id)}><strong>{item.title}</strong><span>{item.last_message_preview || formatDate(item.created_at)}</span></button>)}
        </div>
      </aside>
      <section className="chat-panel">
        <header className="chat-header"><div><p className="eyebrow">LangGraph agent</p><h2>{activeConversation?.title || "Ask your knowledge base"}</h2></div><span className="agent-status"><i /> Online</span></header>
        <div className="message-stream">
          {!activeConversation?.messages?.length && <div className="chat-empty"><span className="chat-symbol">✦</span><h3>What should we look into?</h3><p>Ask about your indexed documents and the agent will search, reason, and cite its sources.</p></div>}
          {activeConversation?.messages?.map((message) => <MessageBubble key={message.id} message={message} onCitation={setCitation} />)}
          {sending && <div className="message assistant-message typing-message"><span /><span /><span /></div>}
          <div ref={messagesEndRef} />
        </div>
        {error && <p className="chat-error" role="alert">{error}</p>}
        <form className="message-composer" onSubmit={sendMessage}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about your documents..." rows="1" onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(event); } }} /><button className="send-button" disabled={!draft.trim() || sending} aria-label="Send message">↑</button></form>
      </section>
      {citation && <CitationPanel citation={citation} onClose={() => setCitation(null)} />}
    </div>
  );
}

function MessageBubble({ message, onCitation }) {
  const isAssistant = message.role === "assistant";
  return <article className={`message ${isAssistant ? "assistant-message" : "user-message"}`}><div className="message-label">{isAssistant ? "Agent" : "You"}</div><div className="message-content">{message.content}</div>{isAssistant && message.citations?.length > 0 && <div className="citation-list">{message.citations.map((item, index) => <button className="citation-chip" key={`${item.filename}-${item.page_number}-${index}`} onClick={() => onCitation(item)}>{item.filename}, p.{item.page_number}</button>)}</div>}</article>;
}

function CitationPanel({ citation, onClose }) {
  return <div className="modal-backdrop" onClick={onClose}><section className="citation-panel" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}><button className="modal-close" onClick={onClose} aria-label="Close citation">×</button><p className="eyebrow">Source citation</p><h3>{citation.filename}</h3><p className="citation-page">Page {citation.page_number}</p>{citation.text && <p className="citation-text">{citation.text}</p>}<button className="primary-button" onClick={onClose}>Close source</button></section></div>;
}