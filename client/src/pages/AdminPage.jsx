import { useCallback, useEffect, useState } from "react";
import { getOrgInvite, getOrgUsage, listOrgMembers } from "../api";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

function formatDate(value) {
  return value ? new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value)) : "—";
}

export function AdminPage() {
  const { token, user } = useAuth();
  const { showToast } = useToast();
  const [members, setMembers] = useState([]);
  const [usage, setUsage] = useState(null);
  const [inviteCode, setInviteCode] = useState("");
  const [loading, setLoading] = useState(true);

  const loadAdminData = useCallback(async () => {
    setLoading(true);
    try {
      const [memberRows, usageStats, invite] = await Promise.all([
        listOrgMembers(token),
        getOrgUsage(token),
        getOrgInvite(token),
      ]);
      setMembers(memberRows);
      setUsage(usageStats);
      setInviteCode(invite.invite_code);
    } catch (error) {
      showToast(error.message);
    } finally {
      setLoading(false);
    }
  }, [showToast, token]);

  useEffect(() => { loadAdminData(); }, [loadAdminData]);

  async function copyInvite() {
    try {
      await navigator.clipboard.writeText(inviteCode);
      showToast("Invite code copied.", "success");
    } catch {
      showToast("Could not copy the invite code.");
    }
  }

  return (
    <div className="workspace-page admin-page">
      <header className="page-header">
        <div><p className="eyebrow">Organization control</p><h2>Keep the workspace in good hands.</h2></div>
        <span className="count-badge">Admin view</span>
      </header>
      {loading ? <AdminSkeleton /> : <>
        <section className="admin-stats">
          <StatCard label="Documents" value={usage?.document_count ?? 0} />
          <StatCard label="Queries" value={usage?.query_count ?? 0} />
          <StatCard label="Members" value={members.length} />
        </section>
        <section className="invite-panel">
          <div><p className="eyebrow">Bring someone in</p><h3>Share the organization invite.</h3><p>New members can use this code in the Join organization flow.</p></div>
          <div className="invite-code-row"><code>{inviteCode || "Unavailable"}</code><button className="primary-button" onClick={copyInvite} disabled={!inviteCode}>Copy code</button></div>
        </section>
        <section className="documents-section">
          <div className="section-heading"><div><p className="eyebrow">Organization roster</p><h3>Members</h3></div><button className="refresh-button" onClick={loadAdminData}>↻ Refresh</button></div>
          <div className="document-table admin-table" role="table" aria-label="Organization members">
            <div className="table-row table-header"><span>Name</span><span>Role</span><span>Joined</span></div>
            {members.map((member) => <div className="table-row" key={member.user_id}><strong>{member.username}{member.user_id === user?.userId ? " (you)" : ""}</strong><span className="role-badge">{member.role}</span><span>{formatDate(member.created_at)}</span></div>)}
          </div>
        </section>
      </>}
    </div>
  );
}

function StatCard({ label, value }) {
  return <div className="stat-card"><span>{label}</span><strong>{value}</strong></div>;
}

function AdminSkeleton() {
  return <div className="admin-skeleton" aria-label="Loading admin data"><span /><span /><span /><div /></div>;
}