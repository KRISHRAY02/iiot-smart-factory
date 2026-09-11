import StatusBadge from "./StatusBadge";

export default function AssetsPage({ assets, onSelect }) {
  if (assets.length === 0) {
    return <div className="empty-state">No assets registered yet.</div>;
  }

  return (
    <div className="assets-grid">
      {assets.map((a) => (
        <button className="asset-card" key={a.asset_id} onClick={() => onSelect(a.asset_id)}>
          <div className="asset-card-header">
            <span className="asset-card-name">{a.name}</span>
            <StatusBadge status={a.status} />
          </div>
          <div className="asset-card-type">{a.asset_type}</div>
          <div className="asset-card-row">
            <span className="asset-card-label">Location</span>
            <span>{a.location || "—"}</span>
          </div>
          <div className="asset-card-row">
            <span className="asset-card-label">Last maintenance</span>
            <span>{a.last_maintenance_date || "—"}</span>
          </div>
          {a.maintenance_overdue && <div className="overdue-badge">Maintenance Overdue</div>}
        </button>
      ))}
    </div>
  );
}
