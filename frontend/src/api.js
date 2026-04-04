const API_BASE_URL = import.meta.env.VITE_API_URL || "https://guidewiredevtrails2026-hackathon.onrender.com";
const AUTH_KEY = "gw_worker_auth_v1";

function getTokens() {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    const auth = raw ? JSON.parse(raw) : null;
    return { accessToken: auth?.access_token || null, refreshToken: auth?.refresh_token || null };
  } catch {
    return { accessToken: null, refreshToken: null };
  }
}

function setAccessToken(newAccessToken) {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    const auth = raw ? JSON.parse(raw) : {};
    auth.access_token = newAccessToken;
    localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
  } catch {
    // ignore
  }
}

async function tryRefresh() {
  const { refreshToken } = getTokens();
  if (!refreshToken) return null;
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/workers/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    setAccessToken(data.access_token);
    return data.access_token;
  } catch {
    return null;
  }
}

async function request(path, options, retry = true) {
  const { accessToken } = getTokens();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  // Auto-refresh: on 401, silently get a new access token and retry once
  if (res.status === 401 && retry) {
    const newToken = await tryRefresh();
    if (newToken) {
      return request(path, options, false); // retry once with fresh token
    }
    // Refresh failed: wipe session and force re-login
    localStorage.removeItem(AUTH_KEY);
    window.dispatchEvent(new Event("gw:session_expired"));
    throw new Error("Session expired — please log in again.");
  }

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const msg = data?.detail || data?.error || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

export async function apiPost(path, body) {
  return request(path, { method: "POST", body: JSON.stringify(body) });
}

export async function apiGet(path) {
  return request(path, { method: "GET" });
}
