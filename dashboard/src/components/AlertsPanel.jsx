import { useState } from "react";
import { acknowledgeAlert, resolveAlert } from "../lib/api";
import { relativeTime } from "../lib/format";

const TYPE_META = {
  threshold_breach: { label: "Threshold Breach", icon: "⛔" },
  statistical_anomaly: { label: "Abnormal Pattern", icon: "📉" },
};

const SEVERITY_ORDER = ["critical", "warning", "info"];
const SEVERITY_LABEL = { critical: "Critical", warning: "Warning", info: "Info" };

function AlertCard({ alert, assetsById, onAcknowledge, onResolve }) {
  const [resolving, setResolving] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const type = TYPE_META[alert.alert_type] || TYPE_META.threshold_breach;
  const asset = alert.asset_id ? assetsById?.[alert.asset_id] : null;
  const acknowledged = alert.status === "acknowledged";

  async function handleAcknowledge() {
    setBusy(true);
    try {
      await onAcknowledge(alert.id);
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmResolve() {
    setBusy(true);
    try {
      await onResolve(alert.id, note.trim() || undefined);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`alert-item severity-${alert.severity} ${acknowledged ? "acknowledged" : ""}`}>
      <div className="alert-item-top">
        <span className="alert-type-icon" aria-hidden="true">
          {type.icon}
        </span>
        <span className={`alert-type-badge ${alert.alert_type || "threshold_breach"}`}>{type.label}</span>
        <span className={`severity-badge ${alert.severity}`}>{alert.severity}</span>
        <span className="alert-time">{relativeTime(alert.created_at)}</span>
      </div>
      <div>
        <strong>{asset ? asset.name : alert.node_id}</strong> · {alert.sensor_type} — {alert.message} (
        {alert.value})
      </div>
      {alert.z_score != null && (
        <div className="alert-zscore">
          {Math.abs(alert.z_score).toFixed(1)}σ from normal
          {alert.baseline_mean != null && alert.baseline_stddev != null
            ? ` (baseline ${alert.baseline_mean.toFixed(2)} ± ${alert.baseline_stddev.toFixed(2)})`
            : ""}
        </div>
      )}
      {acknowledged && (
        <div className="alert-ack-line">
          Acknowledged by {alert.acknowledged_by} · {relativeTime(alert.acknowledged_at)}
        </div>
      )}

      {resolving ? (
        <div className="resolve-note-row">
          <input
            type="text"
            placeholder="Resolution note (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            autoFocus
          />
          <button className="alert-btn resolve" disabled={busy} onClick={handleConfirmResolve}>
            Confirm resolve
          </button>
          <button className="alert-btn" disabled={busy} onClick={() => setResolving(false)}>
            Cancel
          </button>
        </div>
      ) : (
        <div className="alert-actions">
          {!acknowledged && (
            <button className="alert-btn ack" disabled={busy} onClick={handleAcknowledge}>
              Acknowledge
            </button>
          )}
          <button className="alert-btn resolve" disabled={busy} onClick={() => setResolving(true)}>
            Resolve
          </button>
        </div>
      )}
    </div>
  );
}

export default function AlertsPanel({ alerts, assetsById, onChange }) {
  if (alerts.length === 0) {
    return (
      <div className="empty-state-ok">
        <span className="check-icon" aria-hidden="true">
          ✓
        </span>
        <span className="label">All systems nominal</span>
      </div>
    );
  }

  async function handleAcknowledge(id) {
    const updated = await acknowledgeAlert(id);
    onChange?.((prev) => prev.map((a) => (a.id === id ? updated : a)));
  }

  async function handleResolve(id, note) {
    await resolveAlert(id, note);
    onChange?.((prev) => prev.filter((a) => a.id !== id));
  }

  const groups = SEVERITY_ORDER.map((sev) => ({
    severity: sev,
    items: alerts.filter((a) => a.severity === sev),
  })).filter((g) => g.items.length > 0);

  return (
    <>
      {groups.map((g) => (
        <div className="alert-group" key={g.severity}>
          <div className={`alert-group-label ${g.severity}`}>
            {SEVERITY_LABEL[g.severity]} ({g.items.length})
          </div>
          {g.items.map((a) => (
            <AlertCard
              key={a.id}
              alert={a}
              assetsById={assetsById}
              onAcknowledge={handleAcknowledge}
              onResolve={handleResolve}
            />
          ))}
        </div>
      ))}
    </>
  );
}
