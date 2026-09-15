const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "The server could not complete that request.");
  }
  return payload;
}

export function login(username, password) {
  return request("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export function signup({ username, password, orgName, inviteCode }) {
  return request("/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username,
      password,
      ...(orgName ? { org_name: orgName } : { invite_code: inviteCode }),
    }),
  });
}

export function listDocuments(token) {
  return request("/documents", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function uploadDocument(token, file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/documents", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
}

export { API_URL };
