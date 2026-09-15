import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { AuthLayout } from "./LoginPage";
import { useToast } from "../components/Toast";

export function SignupPage() {
  const { signup } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [mode, setMode] = useState("create");
  const [form, setForm] = useState({ username: "", password: "", orgName: "", inviteCode: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signup({ ...form, orgName: mode === "create" ? form.orgName : "", inviteCode: mode === "join" ? form.inviteCode : "" });
      navigate("/documents", { replace: true });
    } catch (requestError) {
      setError(requestError.message);
      showToast(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout eyebrow="Start a workspace" title="Put your knowledge somewhere it can grow." description="Create an organization or join one with its shared invite code.">
      <div className="segmented-control" role="tablist" aria-label="Organization setup">
        <button className={mode === "create" ? "active" : ""} onClick={() => setMode("create")} type="button">Create organization</button>
        <button className={mode === "join" ? "active" : ""} onClick={() => setMode("join")} type="button">Join organization</button>
      </div>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>Username<input required value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></label>
        <label>Password<input required minLength="8" type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>
        {mode === "create" ? <label>Organization name<input required value={form.orgName} onChange={(event) => setForm({ ...form, orgName: event.target.value })} /></label> : <label>Invite code<input required value={form.inviteCode} onChange={(event) => setForm({ ...form, inviteCode: event.target.value })} /></label>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" disabled={busy}>{busy ? "Setting up..." : "Continue"}</button>
      </form>
      <p className="switch-auth">Already have access? <Link to="/login">Sign in</Link></p>
    </AuthLayout>
  );
}
