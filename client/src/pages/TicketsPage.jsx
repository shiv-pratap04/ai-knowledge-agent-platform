import { useCallback, useEffect, useMemo, useState } from "react";
import { createTicket, getTicket, listTickets } from "../api";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

const defaultForm = {
  title: "",
  description: "",
  category: "IT_SUPPORT",
  priority: "MEDIUM",
};

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function TicketsPage() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const [tickets, setTickets] = useState([]);
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [form, setForm] = useState(defaultForm);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  const refreshTickets = useCallback(async () => {
    setLoading(true);
    try {
      const nextTickets = await listTickets(token);
      setTickets(nextTickets);
      if (!selectedTicketId && nextTickets.length) {
        setSelectedTicketId(nextTickets[0].ticket_id);
      }
    } catch (error) {
      showToast(error.message);
    } finally {
      setLoading(false);
    }
  }, [selectedTicketId, token]);

  useEffect(() => { refreshTickets(); }, [refreshTickets]);

  useEffect(() => {
    if (!selectedTicketId) {
      setSelectedTicket(null);
      return;
    }
    const current = tickets.find((ticket) => ticket.ticket_id === selectedTicketId);
    if (current) {
      setSelectedTicket(current);
      return;
    }
    (async () => {
      try {
        const ticket = await getTicket(token, selectedTicketId);
        setSelectedTicket(ticket);
      } catch (error) {
        showToast(error.message);
      }
    })();
  }, [selectedTicketId, tickets, token]);

  const ticketSummary = useMemo(() => selectedTicket ? `${selectedTicket.ticket_id} • ${selectedTicket.status}` : "No ticket selected", [selectedTicket]);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const created = await createTicket(token, form);
      setForm(defaultForm);
      setSelectedTicketId(created.ticket_id);
      await refreshTickets();
      setSelectedTicket(created);
      showToast(`Ticket ${created.ticket_id} created.`);
    } catch (error) {
      showToast(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="workspace-page ticket-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Support desk</p>
          <h2>Internal IT and support tickets</h2>
        </div>
        <span className="count-badge">{tickets.length.toString().padStart(2, "0")} tickets</span>
      </header>

      <section className="ticket-panel">
        <div className="ticket-form-header">
          <p className="eyebrow">Create a ticket</p>
          <h3>Report an issue</h3>
        </div>
        <form className="ticket-form" onSubmit={handleSubmit}>
          <label>
            <span>Title</span>
            <input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="VPN connection failure" required />
          </label>
          <label>
            <span>Description</span>
            <textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="Describe the issue, environment, and impact." rows="4" required />
          </label>
          <div className="ticket-form-grid">
            <label>
              <span>Category</span>
              <select value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}>
                <option value="IT_SUPPORT">IT_SUPPORT</option>
                <option value="NETWORK">NETWORK</option>
                <option value="HARDWARE">HARDWARE</option>
                <option value="SOFTWARE">SOFTWARE</option>
                <option value="ACCESS">ACCESS</option>
                <option value="ACCOUNT">ACCOUNT</option>
                <option value="OTHER">OTHER</option>
              </select>
            </label>
            <label>
              <span>Priority</span>
              <select value={form.priority} onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value }))}>
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </label>
          </div>
          <button className="primary-button" disabled={submitting}>{submitting ? "Creating ticket..." : "Create ticket"}</button>
        </form>
      </section>

      <section className="ticket-list-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Ticket queue</p>
            <h3>Recent support requests</h3>
          </div>
          <button className="refresh-button" onClick={refreshTickets} disabled={loading}>↻ Refresh</button>
        </div>

        {loading ? (
          <div className="empty-state">Loading tickets...</div>
        ) : tickets.length === 0 ? (
          <div className="empty-state">No support tickets yet. Use the form to open one.</div>
        ) : (
          <div className="ticket-layout">
            <div className="ticket-list" role="list">
              {tickets.map((ticket) => (
                <button
                  key={ticket.ticket_id}
                  className={`ticket-item ${selectedTicketId === ticket.ticket_id ? "active" : ""}`}
                  onClick={() => setSelectedTicketId(ticket.ticket_id)}
                  type="button"
                >
                  <span className="ticket-id">{ticket.ticket_id}</span>
                  <strong>{ticket.title}</strong>
                  <div className="ticket-meta">
                    <span>{ticket.category}</span>
                    <span>{ticket.priority}</span>
                    <span>{ticket.status}</span>
                  </div>
                </button>
              ))}
            </div>

            <aside className="ticket-detail">
              {selectedTicket ? (
                <>
                  <p className="eyebrow">Selected ticket</p>
                  <h3>{selectedTicket.ticket_id}</h3>
                  <p className="ticket-summary">{ticketSummary}</p>
                  <dl>
                    <div><dt>Title</dt><dd>{selectedTicket.title}</dd></div>
                    <div><dt>Description</dt><dd>{selectedTicket.description}</dd></div>
                    <div><dt>Category</dt><dd>{selectedTicket.category}</dd></div>
                    <div><dt>Priority</dt><dd>{selectedTicket.priority}</dd></div>
                    <div><dt>Status</dt><dd>{selectedTicket.status}</dd></div>
                    <div><dt>Creator</dt><dd>{selectedTicket.created_by || "Unknown"}</dd></div>
                    <div><dt>Created</dt><dd>{formatDate(selectedTicket.created_at)}</dd></div>
                    <div><dt>Updated</dt><dd>{formatDate(selectedTicket.updated_at)}</dd></div>
                  </dl>
                </>
              ) : (
                <div className="empty-state">Select a ticket to view details.</div>
              )}
            </aside>
          </div>
        )}
      </section>
    </div>
  );
}
