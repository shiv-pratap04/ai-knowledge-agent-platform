import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

export function LoginPage() {
  const { login } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(form.username, form.password);
      navigate(location.state?.from?.pathname || "/documents", { replace: true });
    } catch (requestError) {
      setError(requestError.message);
      showToast(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout eyebrow="Welcome back" title="Return to your research desk." description="Sign in to reach the documents shared with your organization.">
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>Username<input required value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></label>
        <label>Password<input required type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" disabled={busy}>{busy ? "Signing in..." : "Sign in"}</button>
      </form>
      <p className="switch-auth">New workspace? <Link to="/signup">Create an account</Link></p>
    </AuthLayout>
  );
}

export function AuthLayout({ eyebrow, title, description, children }) {
  return (
    <div className="auth-page">
      <section className="auth-panel">
        <div className="brand-lockup"><span className="brand-mark">AR</span><span>Archive Room</span></div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="auth-description">{description}</p>
        {children}
      </section>
      <section className="auth-aside"><span className="aside-number">01</span><p>Make the useful parts of your knowledge easy to return to.</p></section>
    </div>
  );
}
