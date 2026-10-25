import { useMemo, useState } from "react";
import { acknowledgeAlert, resolveAlert } from "../lib/api";
import { relativeTime } from "../lib/format";

const TYPE_META = {
  threshold_breach: { label: "Threshold Breach", icon: "⛔" },
  statistical_anomaly: { label: "Abnormal Pattern", icon: "📉" },
  node_offline: { label: "Node Offline", icon: "🔌" },
};

const SEVERITY_ORDER = ["critical", "warning", "info"];
const SEVERITY_LABEL = { critical: "Critical", warning: "Warning", info: "Info" };
const SEVERITY_ICON = { critical: "🔴", warning: "🟠", info: "🔵" };
const SHOW_LIMIT = 5;
const ONE_HOUR_MS = 60 * 60 * 1000;

function shortMessage(alert) {
  if (alert.z_score != null) {
    return `${Math.abs(alert.z_score).toFixed(1)}σ ${alert.condition} normal, ${alert.value}`;
  }
  return `${alert.message} (${alert.value})`;
}

function AlertDetailRow({ alert, assetsById, onAcknowledge, onResolve }) {
  const [resolving, setResolving] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const type = TYPE_META[alert.alert_type] || TYPE_META.threshold_breach;
  const asset = alert.asset_id ? assetsById?.[alert.asset_id] : null;
  const acknowledged = alert.status === "acknowledged";

  async function handleAck(e) {
    e.stopPropagation();
    setBusy(true);
    try {
      await onAcknowledge(alert.id);
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmResolve(e) {
    e.stopPropagation();
    setBusy(true);
    try {
      await onResolve(alert.id, note.trim() || undefined);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="alert-detail" onClick={(e) => e.stopPropagation()}>
      <div className="alert-detail-meta">
        <span className={`alert-type-badge ${alert.alert_type || "threshold_breach"}`}>
          {type.icon} {type.label}
        </span>
        <span>{asset ? asset.name : alert.node_id}</span>
        <span>·</span>
        <span>{alert.sensor_type}</span>
      </div>
      <div className="alert-detail-message">{alert.message}</div>
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
            onClick={(e) => e.stopPropagation()}
            autoFocus
          />
          <button className="alert-btn resolve" disabled={busy} onClick={handleConfirmResolve}>
            Confirm resolve
          </button>
          <button className="alert-btn" disabled={busy} onClick={(e) => {
            e.stopPropagation();
            setResolving(false);
          }}>
            Cancel
          </button>
        </div>
      ) : (
        <div className="alert-actions">
          {!acknowledged && (
            <button className="alert-btn ack" disabled={busy} onClick={handleAck} title="Acknowledge">
              ✓ Acknowledge
            </button>
          )}
          <button
            className="alert-btn resolve"
            disabled={busy}
            onClick={(e) => {
              e.stopPropagation();
              setResolving(true);
            }}
            title="Resolve"
          >
            ✔ Resolve
          </button>
        </div>
      )}
    </div>
  );
}

function AlertRow({ group, assetsById, onAcknowledge, onResolve }) {
  const [expanded, setExpanded] = useState(false);
  const head = group.items[0];
  const type = TYPE_META[head.alert_type] || TYPE_META.threshold_breach;
  const asset = head.asset_id ? assetsById?.[head.asset_id] : null;
  const isGroup = group.items.length > 1;

  return (
    <div className={`alert-row-wrap severity-${head.severity}`}>
      <div
        className={`alert-row ${head.status === "acknowledged" ? "acknowledged" : ""} ${expanded ? "expanded" : ""}`}
        onClick={() => setExpanded((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") setExpanded((v) => !v);
        }}
      >
        <span className="alert-row-icon" title={type.label} aria-hidden="true">
          {type.icon}
        </span>
        <div className="alert-row-main">
          <div className="alert-row-title">
            <strong>{asset ? asset.name : head.node_id}</strong>
            <span className="alert-row-sensor"> · {head.sensor_type}</span>
            {isGroup && <span className="alert-repeat-badge">×{group.items.length}</span>}
          </div>
          <div className="alert-row-message">{shortMessage(head)}</div>
        </div>
        <span className="alert-row-time">{relativeTime(head.created_at)}</span>
        {!isGroup && (
          <div className="alert-row-actions" onClick={(e) => e.stopPropagation()}>
            {head.status !== "acknowledged" && (
              <button
                className="icon-btn ack"
                title="Acknowledge"
                onClick={async () => {
                  await onAcknowledge(head.id);
                }}
              >
                ✓
              </button>
            )}
            <button
              className="icon-btn resolve"
              title="Resolve"
              onClick={() => setExpanded(true)}
            >
              ✔
            </button>
          </div>
        )}
        <span className="alert-row-chevron" aria-hidden="true">
          {expanded ? "▾" : "▸"}
        </span>
      </div>
      {expanded && (
        <div className="alert-row-detail-list">
          {group.items.map((alert) => (
            <AlertDetailRow
              key={alert.id}
              alert={alert}
              assetsById={assetsById}
              onAcknowledge={onAcknowledge}
              onResolve={onResolve}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SeverityGroup({ severity, alerts, assetsById, onAcknowledge, onResolve }) {
  const [collapsed, setCollapsed] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const groups = useMemo(() => {
    const byKey = new Map();
    for (const alert of alerts) {
      const key = `${alert.node_id}|${alert.alert_type}`;
      if (!byKey.has(key)) byKey.set(key, []);
      byKey.get(key).push(alert);
    }
    return [...byKey.values()]
      .map((items) => ({ items: items.sort((a, b) => (a.created_at < b.created_at ? 1 : -1)) }))
      .sort((a, b) => (a.items[0].created_at < b.items[0].created_at ? 1 : -1));
  }, [alerts]);

  const visible = showAll ? groups : groups.slice(0, SHOW_LIMIT);

  return (
    <div className="alert-group">
      <button className="alert-group-label" onClick={() => setCollapsed((v) => !v)} aria-expanded={!collapsed}>
        <span aria-hidden="true">{SEVERITY_ICON[severity]}</span>
        {SEVERITY_LABEL[severity]} ({alerts.length})
        <span className="chevron" aria-hidden="true">
          {collapsed ? "▸" : "▾"}
        </span>
      </button>
      {!collapsed && (
        <>
          {visible.map((group) => (
            <AlertRow
              key={`${group.items[0].node_id}|${group.items[0].alert_type}`}
              group={group}
              assetsById={assetsById}
              onAcknowledge={onAcknowledge}
              onResolve={onResolve}
            />
          ))}
          {groups.length > SHOW_LIMIT && !showAll && (
            <button className="alerts-show-all" onClick={() => setShowAll(true)}>
              Show all ({groups.length})
            </button>
          )}
        </>
      )}
    </div>
  );
}

export default function AlertsPanel({ alerts, assetsById, onChange }) {
  const [confirmingBulk, setConfirmingBulk] = useState(false);
  const [bulkBusy, setBulkBusy] = useState(false);

  async function handleAcknowledge(id) {
    const updated = await acknowledgeAlert(id);
    onChange?.((prev) => prev.map((a) => (a.id === id ? updated : a)));
  }

  async function handleResolve(id, note) {
    await resolveAlert(id, note);
    onChange?.((prev) => prev.filter((a) => a.id !== id));
  }

  const oldAlerts = useMemo(() => {
    const cutoff = Date.now() - ONE_HOUR_MS;
    return alerts.filter((a) => new Date(a.created_at).getTime() < cutoff);
  }, [alerts]);

  async function handleBulkResolve() {
    setBulkBusy(true);
    try {
      const ids = oldAlerts.map((a) => a.id);
      for (const id of ids) {
        try {
          await resolveAlert(id, "Bulk-resolved: older than 1 hour");
        } catch {
          // keep going even if one fails (e.g. already resolved by someone else)
        }
      }
      onChange?.((prev) => prev.filter((a) => !ids.includes(a.id)));
    } finally {
      setBulkBusy(false);
      setConfirmingBulk(false);
    }
  }

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

  const groups = SEVERITY_ORDER.map((sev) => ({
    severity: sev,
    items: alerts.filter((a) => a.severity === sev),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="alerts-panel">
      {oldAlerts.length > 0 && (
        <div className="alerts-bulk-row">
          {confirmingBulk ? (
            <div className="alerts-bulk-confirm">
              <span>Resolve {oldAlerts.length} alert{oldAlerts.length === 1 ? "" : "s"} older than 1h?</span>
              <button className="alert-btn resolve" disabled={bulkBusy} onClick={handleBulkResolve}>
                {bulkBusy ? "Resolving…" : "Confirm"}
              </button>
              <button className="alert-btn" disabled={bulkBusy} onClick={() => setConfirmingBulk(false)}>
                Cancel
              </button>
            </div>
          ) : (
            <button className="alerts-bulk-resolve" onClick={() => setConfirmingBulk(true)}>
              Resolve all older than 1h ({oldAlerts.length})
            </button>
          )}
        </div>
      )}
      <div className="alerts-panel-scroll">
        {groups.map((g) => (
          <SeverityGroup
            key={g.severity}
            severity={g.severity}
            alerts={g.items}
            assetsById={assetsById}
            onAcknowledge={handleAcknowledge}
            onResolve={handleResolve}
          />
        ))}
      </div>
    </div>
  );
}
