import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AlertHistoryPage from "./components/AlertHistoryPage";
import AlertsPanel from "./components/AlertsPanel";
import AssetDetail from "./components/AssetDetail";
import AssetsPage from "./components/AssetsPage";
import DemoControlsPanel from "./components/DemoControlsPanel";
import ExportPanel from "./components/ExportPanel";
import HistoryChart from "./components/HistoryChart";
import Login from "./components/Login";
import LiveReadings from "./components/LiveReadings";
import StatusBar from "./components/StatusBar";
import SummaryStrip from "./components/SummaryStrip";
import {
  clearToken,
  fetchAlerts,
  fetchAssets,
  fetchNodeHealth,
  fetchStatus,
  getToken,
  onUnauthorized,
  openLiveSocket,
} from "./lib/api";

const HISTORY_LENGTH = 30;

function DashboardView({
  readings,
  alerts,
  setAlerts,
  refreshKey,
  assetsByNode,
  assetsById,
  nodeHealthByNode,
  readingsHistory,
  selectedNode,
  setSelectedNode,
  lastReadingAt,
  wsConnected,
  alertsPanelRef,
  nodeLabel,
  knownNodeIds,
}) {
  const alertsForChart = useMemo(
    () => (selectedNode ? alerts.filter((a) => a.node_id === selectedNode) : []),
    [alerts, selectedNode]
  );

  function scrollToAlerts() {
    alertsPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <>
      <SummaryStrip
        nodeHealthByNode={nodeHealthByNode}
        alerts={alerts}
        assets={Object.values(assetsById)}
        lastUpdate={lastReadingAt}
        wsConnected={wsConnected}
        onAlertsClick={scrollToAlerts}
      />

      <div className="dashboard-main">
        <div className="dashboard-col dashboard-col-left">
          <div className="panel">
            <div className="panel-header">
              <h2>Live Sensor Readings</h2>
            </div>
            <LiveReadings
              readings={readings}
              assetsByNode={assetsByNode}
              nodeHealthByNode={nodeHealthByNode}
              readingsHistory={readingsHistory}
              selectedNode={selectedNode}
              onSelectNode={setSelectedNode}
            />
          </div>
          <DemoControlsPanel nodeIds={knownNodeIds} nodeLabel={nodeLabel} />
        </div>

        <div className="dashboard-col dashboard-col-right">
          <div className="panel alerts-panel-card" ref={alertsPanelRef}>
            <div className="panel-header">
              <h2>Active Alerts</h2>
            </div>
            <AlertsPanel alerts={alerts} assetsById={assetsById} onChange={setAlerts} />
          </div>
        </div>
      </div>

      <div className="panel chart-panel">
        <div className="panel-header">
          <h2>Historical Trend</h2>
        </div>
        <HistoryChart
          refreshKey={refreshKey}
          nodeOptions={knownNodeIds}
          nodeLabel={nodeLabel}
          selectedNode={selectedNode}
          onSelectNode={setSelectedNode}
          alertsForChart={alertsForChart}
        />
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Export</h2>
        </div>
        <ExportPanel assets={Object.values(assetsById)} />
      </div>
    </>
  );
}

function Shell({ onLogout }) {
  const [readings, setReadings] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [assets, setAssets] = useState([]);
  const [nodeHealth, setNodeHealth] = useState([]);
  const [view, setView] = useState("dashboard");
  const [selectedAssetId, setSelectedAssetId] = useState(null);
  const [selectedNode, setSelectedNode] = useState("");
  const [readingsHistory, setReadingsHistory] = useState({});
  const [lastReadingAt, setLastReadingAt] = useState(null);
  const [, setTick] = useState(0);
  const alertsPanelRef = useRef(null);

  const loadAlerts = useCallback(() => {
    fetchAlerts().then(setAlerts).catch(() => {});
  }, []);

  const loadStatus = useCallback(() => {
    fetchStatus().then(setStatus).catch(() => {});
  }, []);

  const loadAssets = useCallback(() => {
    fetchAssets().then(setAssets).catch(() => {});
  }, []);

  const loadNodeHealth = useCallback(() => {
    fetchNodeHealth().then(setNodeHealth).catch(() => {});
  }, []);

  useEffect(() => {
    loadAlerts();
    loadStatus();
    loadAssets();
    loadNodeHealth();
    const statusInterval = setInterval(loadStatus, 5000);
    const assetsInterval = setInterval(loadAssets, 10000);
    const healthInterval = setInterval(loadNodeHealth, 5000);
    const tickInterval = setInterval(() => setTick((t) => t + 1), 3000);
    return () => {
      clearInterval(statusInterval);
      clearInterval(assetsInterval);
      clearInterval(healthInterval);
      clearInterval(tickInterval);
    };
  }, [loadAlerts, loadStatus, loadAssets, loadNodeHealth]);

  useEffect(() => {
    const ws = openLiveSocket((msg) => {
      if (msg.type === "reading") {
        setReadings((prev) => ({ ...prev, [msg.data.node_id]: msg.data }));
        setReadingsHistory((prev) => {
          const existing = prev[msg.data.node_id] || [];
          const next = [...existing, msg.data.value].slice(-HISTORY_LENGTH);
          return { ...prev, [msg.data.node_id]: next };
        });
        setLastReadingAt(new Date().toISOString());
        setRefreshKey((k) => k + 1);
      } else if (msg.type === "alert") {
        setAlerts((prev) => [msg.data, ...prev.filter((a) => a.id !== msg.data.id)].slice(0, 200));
      } else if (msg.type === "node_health") {
        setNodeHealth(msg.data);
      }
    });
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);
    return () => ws.close();
  }, []);

  const nodeHealthByNode = useMemo(() => {
    const map = {};
    for (const h of nodeHealth) {
      map[h.node_id] = h;
    }
    return map;
  }, [nodeHealth]);

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

  const knownNodeIds = useMemo(() => {
    const ids = new Set([...Object.keys(readings), ...Object.keys(nodeHealthByNode)]);
    return [...ids].sort((a, b) => a.localeCompare(b));
  }, [readings, nodeHealthByNode]);

  const nodeLabel = useMemo(() => {
    const map = {};
    for (const nodeId of knownNodeIds) {
      const asset = assetsByNode[nodeId];
      const sensorType = readings[nodeId]?.sensor_type || nodeHealthByNode[nodeId]?.sensor_type;
      map[nodeId] = asset ? `${asset.name} · ${sensorType || nodeId}` : nodeId;
    }
    return map;
  }, [knownNodeIds, assetsByNode, readings, nodeHealthByNode]);

  useEffect(() => {
    if (!selectedNode && knownNodeIds.length > 0) {
      setSelectedNode(knownNodeIds[0]);
    }
  }, [selectedNode, knownNodeIds]);

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
        <div className="topbar-left">
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
        <div className="topbar-right">
          <StatusBar status={status} wsConnected={wsConnected} />
          <button className="logout-btn" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </div>

      <div className="app-content">
        {view === "dashboard" && (
          <DashboardView
            readings={readings}
            alerts={alerts}
            setAlerts={setAlerts}
            refreshKey={refreshKey}
            assetsByNode={assetsByNode}
            assetsById={assetsById}
            nodeHealthByNode={nodeHealthByNode}
            readingsHistory={readingsHistory}
            selectedNode={selectedNode}
            setSelectedNode={setSelectedNode}
            lastReadingAt={lastReadingAt}
            wsConnected={wsConnected}
            alertsPanelRef={alertsPanelRef}
            nodeLabel={nodeLabel}
            knownNodeIds={knownNodeIds}
          />
        )}
        {view === "assets" && <AssetsPage assets={assets} onSelect={openAsset} />}
        {view === "asset-detail" && selectedAssetId && (
          <AssetDetail assetId={selectedAssetId} onBack={backToAssets} />
        )}
        {view === "alert-history" && <AlertHistoryPage assets={assets} />}
      </div>
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
