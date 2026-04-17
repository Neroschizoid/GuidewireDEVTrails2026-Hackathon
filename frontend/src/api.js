const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:8000" : "https://guidewiredevtrails2026-hackathon.onrender.com");
import { clearAuthSession, getTokens, setAccessToken } from "./authStorage";

async function tryRefresh() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/workers/refresh`, {
      method: "POST",
      credentials: "include",
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

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, credentials: "include" });

  // Auto-refresh: on 401, silently get a new access token and retry once
  if (res.status === 401 && retry) {
    const newToken = await tryRefresh();
    if (newToken) {
      return request(path, options, false); // retry once with fresh token
    }
    // Refresh failed: wipe session and force re-login
    clearAuthSession();
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
    let msg = data?.detail || data?.error || `HTTP ${res.status}`;
    if (typeof msg !== "string") {
      try {
        msg = JSON.stringify(msg);
      } catch {
        msg = "Unknown API Error";
      }
    }
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

export async function apiDelete(path) {
  return request(path, { method: "DELETE" });
}

export async function apiLogout() {
  try {
    await fetch(`${API_BASE_URL}/api/v1/workers/logout`, {
      method: "POST",
      credentials: "include",
    });
  } finally {
    clearAuthSession();
  }
}
