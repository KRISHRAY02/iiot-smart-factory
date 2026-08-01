export default function AlertsPanel({ alerts }) {
  if (alerts.length === 0) {
    return <div className="empty-state">No alerts — all systems nominal.</div>;
  }

  return (
    <>
      {alerts.map((a, i) => (
        <div className="alert-item" key={a.id || i}>
          <span className={`severity-badge ${a.severity}`}>{a.severity}</span>
          <strong>{a.node_id}</strong> — {a.message} ({a.value})
          <div style={{ color: "var(--gray-600)", fontSize: "0.75rem" }}>
            {new Date(a.timestamp).toLocaleString()}
          </div>
        </div>
      ))}
    </>
  );
}
