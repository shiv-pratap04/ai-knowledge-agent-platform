import { createContext, useContext, useMemo, useState } from "react";
import { login as loginRequest, signup as signupRequest } from "../api";

const AuthContext = createContext(null);

function decodeToken(token) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);

  function applyToken(nextToken) {
    const decoded = decodeToken(nextToken);
    if (!decoded?.sub || !decoded?.org_id || !decoded?.role) {
      throw new Error("The server returned an invalid session token.");
    }
    setToken(nextToken);
    setUser({
      username: decoded.sub,
      userId: decoded.user_id,
      orgId: decoded.org_id,
      role: decoded.role,
    });
  }

  async function login(username, password) {
    const result = await loginRequest(username, password);
    applyToken(result.access_token);
  }

  async function signup(values) {
    await signupRequest(values);
    await login(values.username, values.password);
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({ token, user, login, signup, logout }),
    [token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
