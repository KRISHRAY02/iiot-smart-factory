import { useCallback, useEffect, useMemo, useState } from "react";
import AlertHistoryPage from "./components/AlertHistoryPage";
import AlertsPanel from "./components/AlertsPanel";
import AssetDetail from "./components/AssetDetail";
import AssetsPage from "./components/AssetsPage";
import HistoryChart from "./components/HistoryChart";
import Login from "./components/Login";
import LiveReadings from "./components/LiveReadings";
import StatusBar from "./components/StatusBar";
import {
  clearToken,
  fetchAlerts,
  fetchAssets,
  fetchStatus,
  getToken,
  onUnauthorized,
  openLiveSocket,
} from "./lib/api";

function DashboardView({ readings, alerts, setAlerts, refreshKey, assetsByNode, assetsById }) {
  return (
    <div className="dashboard-grid">
      <div className="card">
        <h2>Live Sensor Readings</h2>
        <LiveReadings readings={readings} assetsByNode={assetsByNode} />
      </div>
      <div className="card">
        <h2>Active Alerts</h2>
        <AlertsPanel alerts={alerts} assetsById={assetsById} onChange={setAlerts} />
      </div>
      <div className="card span-2">
        <h2>Historical Trend</h2>
        <HistoryChart refreshKey={refreshKey} />
      </div>
    </div>
  );
}

function Shell({ onLogout }) {
  const [readings, setReadings] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [assets, setAssets] = useState([]);
  const [view, setView] = useState("dashboard");
  const [selectedAssetId, setSelectedAssetId] = useState(null);

  const loadAlerts = useCallback(() => {
    fetchAlerts().then(setAlerts).catch(() => {});
  }, []);

  const loadStatus = useCallback(() => {
    fetchStatus().then(setStatus).catch(() => {});
  }, []);

  const loadAssets = useCallback(() => {
    fetchAssets().then(setAssets).catch(() => {});
  }, []);

  useEffect(() => {
    loadAlerts();
    loadStatus();
    loadAssets();
    const statusInterval = setInterval(loadStatus, 5000);
    const assetsInterval = setInterval(loadAssets, 10000);
    return () => {
      clearInterval(statusInterval);
      clearInterval(assetsInterval);
    };
  }, [loadAlerts, loadStatus, loadAssets]);

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

  const assetsByNode = useMemo(() => {
    const map = {};
    for (const asset of assets) {
      for (const nodeId of asset.linked_sensor_nodes) {
        map[nodeId] = asset;
      }
    }
    return map;
  }, [assets]);

  const assetsById = useMemo(() => {
    const map = {};
    for (const asset of assets) {
      map[asset.asset_id] = asset;
    }
    return map;
  }, [assets]);

  function handleLogout() {
    clearToken();
    onLogout();
  }

  function openAsset(assetId) {
    setSelectedAssetId(assetId);
    setView("asset-detail");
  }

  function backToAssets() {
    setSelectedAssetId(null);
    setView("assets");
    loadAssets();
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <h1>IIoT Smart Factory Monitor</h1>
          <nav className="tab-nav">
            <button
              className={`tab-btn ${view === "dashboard" ? "active" : ""}`}
              onClick={() => setView("dashboard")}
            >
              Dashboard
            </button>
            <button
              className={`tab-btn ${view === "assets" || view === "asset-detail" ? "active" : ""}`}
              onClick={() => setView("assets")}
            >
              Assets
            </button>
            <button
              className={`tab-btn ${view === "alert-history" ? "active" : ""}`}
              onClick={() => setView("alert-history")}
            >
              Alert History
            </button>
          </nav>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <StatusBar status={status} wsConnected={wsConnected} />
          <button className="logout-btn" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </div>

      {view === "dashboard" && (
        <DashboardView
          readings={readings}
          alerts={alerts}
          setAlerts={setAlerts}
          refreshKey={refreshKey}
          assetsByNode={assetsByNode}
          assetsById={assetsById}
        />
      )}
      {view === "assets" && <AssetsPage assets={assets} onSelect={openAsset} />}
      {view === "asset-detail" && selectedAssetId && (
        <AssetDetail assetId={selectedAssetId} onBack={backToAssets} />
      )}
      {view === "alert-history" && <AlertHistoryPage assets={assets} />}
    </div>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!getToken());

  useEffect(() => {
    onUnauthorized(() => setLoggedIn(false));
  }, []);

  if (!loggedIn) {
    return <Login onLoggedIn={() => setLoggedIn(true)} />;
  }

  return <Shell onLogout={() => setLoggedIn(false)} />;
}
