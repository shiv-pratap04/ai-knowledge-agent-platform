import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand-mark">AR</div>
        <div>
          <p className="eyebrow">Knowledge workspace</p>
          <h1>Archive Room</h1>
        </div>
        <nav className="nav-links" aria-label="Primary navigation">
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/documents">Documents</NavLink>
          <NavLink to="/tickets">Tickets</NavLink>
          {user?.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <span className="avatar">{user?.username?.slice(0, 1).toUpperCase()}</span>
            <span>
              <strong>{user?.username}</strong>
              <small>{user?.role} · {user?.orgId?.slice(0, 8)}</small>
            </span>
          </div>
          <button className="text-button" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main-content"><Outlet /></main>
    </div>
  );
}
