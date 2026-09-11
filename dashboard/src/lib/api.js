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

let unauthorizedHandler = null;

export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
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
    if (unauthorizedHandler) unauthorizedHandler();
    throw new Error("Session expired, please log in again");
  }
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function fetchStatus() {
  return authedFetch("/api/status");
}

export function fetchAlerts(assetId) {
  const params = assetId ? `?asset_id=${assetId}` : "";
  return authedFetch(`/api/alerts${params}`);
}

export function acknowledgeAlert(alertId) {
  return authedFetch(`/api/alerts/${alertId}/acknowledge`, { method: "POST" });
}

export function resolveAlert(alertId, resolutionNote) {
  return authedFetch(`/api/alerts/${alertId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolution_note: resolutionNote || null }),
  });
}

export function fetchAlertHistory({ status, severity, assetId, start, end, limit = 200 } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (severity) params.set("severity", severity);
  if (assetId) params.set("asset_id", assetId);
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  params.set("limit", limit);
  return authedFetch(`/api/alerts/history?${params.toString()}`);
}

export function fetchAlertSummary() {
  return authedFetch("/api/alerts/summary");
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

export function triggerAnomaly(nodeId, mode = "spike") {
  return authedFetch(`/api/control/anomaly/${nodeId}?mode=${mode}`, { method: "POST" });
}

export function fetchAssets() {
  return authedFetch("/api/assets");
}

export function fetchAssetDetail(assetId) {
  return authedFetch(`/api/assets/${assetId}/detail`);
}

export function createAsset(payload) {
  return authedFetch("/api/assets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateAsset(assetId, payload) {
  return authedFetch(`/api/assets/${assetId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteAsset(assetId) {
  return authedFetch(`/api/assets/${assetId}`, { method: "DELETE" });
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
