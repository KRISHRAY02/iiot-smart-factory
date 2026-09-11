import { useCallback, useEffect, useState } from "react";
import { fetchAlertHistory, fetchAlertSummary } from "../lib/api";
import { fmtDuration } from "../lib/format";
import AlertHistoryTable from "./AlertHistoryTable";

const STATUS_OPTIONS = ["", "active", "acknowledged", "resolved"];
const SEVERITY_OPTIONS = ["", "critical", "warning", "info"];

export default function AlertHistoryPage({ assets }) {
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [assetId, setAssetId] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [sortAsc, setSortAsc] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    fetchAlertSummary().then(setSummary).catch(() => {});
  }, [alerts]);

  const load = useCallback(() => {
    setLoading(true);
    fetchAlertHistory({
      status: status || undefined,
      severity: severity || undefined,
      assetId: assetId || undefined,
      start: start ? new Date(start).toISOString() : undefined,
      end: end ? new Date(end).toISOString() : undefined,
    })
      .then((rows) => {
        setAlerts(rows);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [status, severity, assetId, start, end]);

  useEffect(() => {
    load();
  }, [load]);

  const assetsById = Object.fromEntries((assets || []).map((a) => [a.asset_id, a]));
  const rows = sortAsc ? [...alerts].reverse() : alerts;

  return (
    <div className="history-page">
      {summary && (
        <div className="stat-cards-row">
          <div className="stat-card">
            <div className="stat-card-label">Active — Critical</div>
            <div className="stat-card-value critical">{summary.active_by_severity.critical}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Active — Warning</div>
            <div className="stat-card-value warning">{summary.active_by_severity.warning}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Active — Info</div>
            <div className="stat-card-value info">{summary.active_by_severity.info}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Avg time to acknowledge</div>
            <div className="stat-card-value">{fmtDuration(summary.avg_time_to_acknowledge_seconds)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card-label">Avg time to resolve</div>
            <div className="stat-card-value">{fmtDuration(summary.avg_time_to_resolve_seconds)}</div>
          </div>
        </div>
      )}

      <div className="history-filters">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s ? s[0].toUpperCase() + s.slice(1) : "All statuses"}
            </option>
          ))}
        </select>
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
          {SEVERITY_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s ? s[0].toUpperCase() + s.slice(1) : "All severities"}
            </option>
          ))}
        </select>
        <select value={assetId} onChange={(e) => setAssetId(e.target.value)}>
          <option value="">All assets</option>
          {(assets || []).map((a) => (
            <option key={a.asset_id} value={a.asset_id}>
              {a.name}
            </option>
          ))}
        </select>
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} title="From date" />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} title="To date" />
        <button className="alert-btn" onClick={() => setSortAsc((v) => !v)}>
          {sortAsc ? "Oldest first" : "Newest first"}
        </button>
      </div>

      {error ? (
        <div className="history-error">{error}</div>
      ) : (
        <AlertHistoryTable alerts={rows} assetsById={assetsById} loading={loading} />
      )}
    </div>
  );
}
