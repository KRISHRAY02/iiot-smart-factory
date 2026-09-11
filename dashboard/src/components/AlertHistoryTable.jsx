import { fmt } from "../lib/format";

export default function AlertHistoryTable({ alerts, assetsById, showAssetColumn = true, loading = false }) {
  return (
    <div className="history-table-wrap">
      <table className="history-table">
        <thead>
          <tr>
            <th>Time</th>
            {showAssetColumn && <th>Asset</th>}
            <th>Sensor</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Acknowledged</th>
            <th>Resolved</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => {
            const asset = a.asset_id ? assetsById?.[a.asset_id] : null;
            return (
              <tr key={a.id}>
                <td>{fmt(a.created_at)}</td>
                {showAssetColumn && <td>{asset ? asset.name : a.node_id}</td>}
                <td>{a.sensor_type}</td>
                <td>
                  <span className={`severity-badge ${a.severity}`}>{a.severity}</span>
                </td>
                <td>
                  <span className={`status-pill-table ${a.status}`}>{a.status}</span>
                </td>
                <td>{a.acknowledged_by ? `${a.acknowledged_by} · ${fmt(a.acknowledged_at)}` : "—"}</td>
                <td>{a.resolved_by ? `${a.resolved_by} · ${fmt(a.resolved_at)}` : "—"}</td>
                <td>{a.resolution_note || "—"}</td>
              </tr>
            );
          })}
          {!loading && alerts.length === 0 && (
            <tr>
              <td colSpan={showAssetColumn ? 8 : 7} className="empty-state">
                No alerts match these filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
