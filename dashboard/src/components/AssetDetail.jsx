import { useCallback, useEffect, useState } from "react";
import { fetchAssetDetail, updateAsset } from "../lib/api";
import AlertHistoryTable from "./AlertHistoryTable";
import HistoryChart from "./HistoryChart";
import LiveReadings from "./LiveReadings";
import StatusBadge from "./StatusBadge";

const STATUS_OPTIONS = ["Operational", "Under Maintenance", "Offline", "Decommissioned"];

export default function AssetDetail({ assetId, onBack }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);
  const [savingStatus, setSavingStatus] = useState(false);

  const load = useCallback(() => {
    fetchAssetDetail(assetId)
      .then((d) => {
        setDetail(d);
        setError(null);
      })
      .catch((err) => setError(err.message));
  }, [assetId]);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  async function handleStatusChange(e) {
    const status = e.target.value;
    setSavingStatus(true);
    try {
      await updateAsset(assetId, { status });
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingStatus(false);
    }
  }

  if (error && !detail) {
    return (
      <div className="dashboard-grid">
        <div className="card span-2">
          <button className="back-link" onClick={onBack}>
            ← Back to Assets
          </button>
          <div className="history-error">{error}</div>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="dashboard-grid">
        <div className="card span-2">
          <div className="empty-state">Loading asset…</div>
        </div>
      </div>
    );
  }

  const { asset, live_readings, alert_history } = detail;
  const readingsByNode = Object.fromEntries(live_readings.map((r) => [r.node_id, r]));

  return (
    <div className="dashboard-grid">
      <div className="card span-2">
        <button className="back-link" onClick={onBack}>
          ← Back to Assets
        </button>
        <div className="asset-detail-header">
          <div>
            <h2 style={{ margin: 0, fontSize: "1.1rem" }}>{asset.name}</h2>
            <div className="reading-type">
              {asset.asset_type} · {asset.location || "no location set"}
            </div>
          </div>
          <StatusBadge status={asset.status} />
        </div>
        {asset.maintenance_overdue && <div className="overdue-badge">Maintenance Overdue</div>}

        <div className="asset-meta-grid">
          <div>
            <span className="asset-card-label">Model</span>
            <div>{asset.model_number || "—"}</div>
          </div>
          <div>
            <span className="asset-card-label">Manufacturer</span>
            <div>{asset.manufacturer || "—"}</div>
          </div>
          <div>
            <span className="asset-card-label">Installed</span>
            <div>{asset.install_date || "—"}</div>
          </div>
          <div>
            <span className="asset-card-label">Last maintenance</span>
            <div>{asset.last_maintenance_date || "—"}</div>
          </div>
          <div>
            <span className="asset-card-label">Next scheduled maintenance</span>
            <div>{asset.next_scheduled_maintenance || "—"}</div>
          </div>
          <div>
            <span className="asset-card-label">Set status</span>
            <select value={asset.status} disabled={savingStatus} onChange={handleStatusChange}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card span-2">
        <h2>Live Sensor Readings</h2>
        <LiveReadings readings={readingsByNode} />
      </div>
      <div className="card span-2">
        <h2>Historical Trend</h2>
        <HistoryChart nodeOptions={asset.linked_sensor_nodes} />
      </div>
      <div className="card span-2">
        <h2>Alert History</h2>
        <AlertHistoryTable alerts={alert_history} showAssetColumn={false} />
      </div>
    </div>
  );
}
