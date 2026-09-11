const TYPE_META = {
  threshold_breach: { label: "Threshold Breach", icon: "⛔" },
  statistical_anomaly: { label: "Abnormal Pattern", icon: "📉" },
};

export default function AlertsPanel({ alerts }) {
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

  return (
    <>
      {alerts.map((a, i) => {
        const type = TYPE_META[a.alert_type] || TYPE_META.threshold_breach;
        return (
          <div className={`alert-item ${a.alert_type || "threshold_breach"}`} key={a.id || i}>
            <div className="alert-item-top">
              <span className="alert-type-icon" aria-hidden="true">
                {type.icon}
              </span>
              <span className={`alert-type-badge ${a.alert_type || "threshold_breach"}`}>{type.label}</span>
              <span className={`severity-badge ${a.severity}`}>{a.severity}</span>
            </div>
            <div>
              <strong>{a.node_id}</strong> — {a.message} ({a.value})
            </div>
            {a.z_score != null && (
              <div className="alert-zscore">
                {Math.abs(a.z_score).toFixed(1)}σ from normal
                {a.baseline_mean != null && a.baseline_stddev != null
                  ? ` (baseline ${a.baseline_mean.toFixed(2)} ± ${a.baseline_stddev.toFixed(2)})`
                  : ""}
              </div>
            )}
            <div style={{ color: "var(--gray-600)", fontSize: "0.75rem" }}>
              {new Date(a.timestamp).toLocaleString()}
            </div>
          </div>
        );
      })}
    </>
  );
}
