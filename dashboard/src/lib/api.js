const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";

const TOKEN_KEY = "iiot_dashboard_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function login(username, password) {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    throw new Error("Invalid username or password");
  }
  const data = await res.json();
  setToken(data.access_token);
  return data.access_token;
}

async function authedFetch(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });
  if (res.status === 401) {
    clearToken();
    throw new Error("Session expired, please log in again");
  }
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

export function fetchStatus() {
  return authedFetch("/api/status");
}

export function fetchAlerts(limit = 100) {
  return authedFetch(`/api/alerts?limit=${limit}`);
}

export function fetchHistory({ nodeId, sensorType, hours = 1 } = {}) {
  const params = new URLSearchParams();
  if (nodeId) params.set("node_id", nodeId);
  if (sensorType) params.set("sensor_type", sensorType);
  params.set("hours", hours);
  return authedFetch(`/api/readings/history?${params.toString()}`);
}

export function fetchNodes() {
  return authedFetch("/api/readings/nodes");
}

export function triggerAnomaly(nodeId) {
  return authedFetch(`/api/control/anomaly/${nodeId}`, { method: "POST" });
}

export function openLiveSocket(onMessage) {
  const token = getToken();
  const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch {
      // ignore malformed frames
    }
  };
  return ws;
}
