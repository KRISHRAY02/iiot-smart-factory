import { useCallback, useEffect, useState } from "react";
import AlertsPanel from "./components/AlertsPanel";
import HistoryChart from "./components/HistoryChart";
import Login from "./components/Login";
import LiveReadings from "./components/LiveReadings";
import StatusBar from "./components/StatusBar";
import { clearToken, fetchAlerts, fetchStatus, getToken, openLiveSocket } from "./lib/api";

function Dashboard({ onLogout }) {
  const [readings, setReadings] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadAlerts = useCallback(() => {
    fetchAlerts(50).then(setAlerts).catch(() => {});
  }, []);

  const loadStatus = useCallback(() => {
    fetchStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    loadAlerts();
    loadStatus();
    const statusInterval = setInterval(loadStatus, 5000);
    return () => clearInterval(statusInterval);
  }, [loadAlerts, loadStatus]);

  useEffect(() => {
    const ws = openLiveSocket((msg) => {
      if (msg.type === "reading") {
        setReadings((prev) => ({ ...prev, [msg.data.node_id]: msg.data }));
        setRefreshKey((k) => k + 1);
      } else if (msg.type === "alert") {
        setAlerts((prev) => [msg.data, ...prev].slice(0, 50));
      }
    });
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);
    return () => ws.close();
  }, []);

  function handleLogout() {
    clearToken();
    onLogout();
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <h1>IIoT Smart Factory Monitor</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <StatusBar status={status} wsConnected={wsConnected} />
          <button className="logout-btn" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </div>
      <div className="dashboard-grid">
        <div className="card">
          <h2>Live Sensor Readings</h2>
          <LiveReadings readings={readings} />
        </div>
        <div className="card">
          <h2>Active Alerts</h2>
          <AlertsPanel alerts={alerts} />
        </div>
        <div className="card span-2">
          <h2>Historical Trend</h2>
          <HistoryChart refreshKey={refreshKey} />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!getToken());

  if (!loggedIn) {
    return <Login onLoggedIn={() => setLoggedIn(true)} />;
  }

  return <Dashboard onLogout={() => setLoggedIn(false)} />;
}
