import { relativeTime } from "../lib/format";

export default function SummaryStrip({ nodeHealthByNode, alerts, assets, lastUpdate, wsConnected, onAlertsClick }) {
  const nodes = Object.values(nodeHealthByNode || {});
  const onlineCount = nodes.filter((n) => n.state === "online").length;
  const nodesLevel = nodes.length === 0 || onlineCount === nodes.length ? "ok" : onlineCount === 0 ? "danger" : "warn";

  const severityCounts = { critical: 0, warning: 0, info: 0 };
  for (const a of alerts) {
    if (severityCounts[a.severity] != null) severityCounts[a.severity] += 1;
  }
  const totalAlerts = alerts.length;
  const alertsLevel = severityCounts.critical > 0 ? "danger" : severityCounts.warning > 0 ? "warn" : "ok";

  const relevantAssets = (assets || []).filter((a) => a.status !== "Decommissioned");
  const operationalCount = relevantAssets.filter((a) => a.status === "Operational").length;
  const assetsLevel =
    relevantAssets.length === 0 || operationalCount === relevantAssets.length
      ? "ok"
      : operationalCount === 0
        ? "danger"
        : "warn";

  return (
    <div className="summary-strip">
      <div className={`kpi-card kpi-${nodesLevel}`} title="Sensor nodes currently reporting online">
        <div className="kpi-label">Nodes online</div>
        <div className="kpi-value">
          {onlineCount} / {nodes.length}
        </div>
      </div>

      <button
        className={`kpi-card kpi-${alertsLevel} kpi-clickable`}
        onClick={onAlertsClick}
        title="Jump to the Active Alerts panel"
      >
        <div className="kpi-label">Active alerts</div>
        <div className="kpi-value">{totalAlerts}</div>
        <div className="kpi-breakdown">
          <span className="kpi-chip critical" title="Critical">
            {severityCounts.critical}
          </span>
          <span className="kpi-chip warning" title="Warning">
            {severityCounts.warning}
          </span>
          <span className="kpi-chip info" title="Info">
            {severityCounts.info}
          </span>
        </div>
      </button>

      <div className={`kpi-card kpi-${assetsLevel}`} title="Assets currently in Operational status">
        <div className="kpi-label">Assets operational</div>
        <div className="kpi-value">
          {operationalCount} / {relevantAssets.length}
        </div>
      </div>

      <div className="kpi-card kpi-neutral" title="Time since the last live reading arrived">
        <div className="kpi-label">Last update</div>
        <div className="kpi-value kpi-value-sm">
          <span className={`live-dot ${wsConnected ? "ok" : "down"}`} aria-hidden="true" />
          {lastUpdate ? `updated ${relativeTime(lastUpdate)}` : "waiting…"}
        </div>
      </div>
    </div>
  );
}
