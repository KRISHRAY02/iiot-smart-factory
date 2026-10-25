import { relativeTime } from "../lib/format";
import { iconFor } from "../lib/sensorIcons";
import Sparkline from "./Sparkline";

const HEALTH_LABEL = { online: "Online", stale: "Stale", offline: "Offline" };

function HealthBadge({ health }) {
  if (!health) return null;
  const state = health.state || "offline";
  return (
    <div
      className={`sensor-health-badge ${state}`}
      title={health?.last_seen ? `Last seen ${relativeTime(health.last_seen)}` : "Never reported"}
    >
      <span className={`health-dot ${state}`} aria-hidden="true" />
      <span>{HEALTH_LABEL[state]}</span>
      {health?.last_seen != null && <span className="sensor-health-last-seen">· {relativeTime(health.last_seen)}</span>}
    </div>
  );
}

export default function LiveReadings({ readings, assetsByNode, nodeHealthByNode, readingsHistory, selectedNode, onSelectNode }) {
  const nodeIds = new Set([...Object.keys(readings), ...Object.keys(nodeHealthByNode || {})]);
  const nodes = [...nodeIds]
    .sort((a, b) => a.localeCompare(b))
    .map((nodeId) => ({ nodeId, reading: readings[nodeId], health: nodeHealthByNode?.[nodeId] }));

  if (nodes.length === 0) {
    return <div className="empty-state">Waiting for first reading…</div>;
  }

  return (
    <div className="sensor-grid">
      {nodes.map(({ nodeId, reading: r, health }) => {
        const asset = assetsByNode?.[nodeId];
        const isOffline = health?.state === "offline";
        const hasBand = !isOffline && r?.rolling_mean != null && r?.rolling_stddev != null;
        const bandLower = hasBand ? r.rolling_mean - 2 * r.rolling_stddev : null;
        const bandUpper = hasBand ? r.rolling_mean + 2 * r.rolling_stddev : null;
        const outsideBand = hasBand && (r.value < bandLower || r.value > bandUpper);
        const sensorType = r?.sensor_type || health?.sensor_type;
        const history = readingsHistory?.[nodeId] || [];

        let statusClass = "ok";
        if (isOffline) statusClass = "offline";
        else if (r?.anomaly) statusClass = "danger";
        else if (outsideBand) statusClass = "warn";

        const title = asset ? `${asset.name}` : nodeId;
        const isSelected = selectedNode === nodeId;

        return (
          <button
            key={nodeId}
            className={`sensor-card status-${statusClass} ${isSelected ? "selected" : ""}`}
            onClick={() => onSelectNode?.(nodeId)}
            title={`Select ${title} in the trend chart below`}
          >
            <HealthBadge health={health} />
            <div className="sensor-card-head">
              <span className="sensor-icon" aria-hidden="true">
                {iconFor(sensorType)}
              </span>
              <div className="sensor-names">
                <div className="sensor-asset-name">{title}</div>
                <div className="sensor-type-label">{sensorType || "unknown"}</div>
                {asset?.location && <div className="sensor-location">{asset.location}</div>}
              </div>
            </div>

            <div className={`sensor-value-row status-${statusClass}`}>
              {isOffline ? (
                <span className="sensor-value sensor-value-nodata">No data</span>
              ) : r ? (
                <>
                  <span className="sensor-value">{r.value}</span>
                  <span className="sensor-unit">{r.unit}</span>
                </>
              ) : (
                <span className="sensor-value sensor-value-nodata">—</span>
              )}
            </div>

            {hasBand && (
              <div className={`sensor-range ${outsideBand ? "outside" : ""}`}>
                Normal range: {bandLower.toFixed(1)}–{bandUpper.toFixed(1)} {r.unit}
              </div>
            )}

            <Sparkline values={history} bandLower={bandLower} bandUpper={bandUpper} />
          </button>
        );
      })}
    </div>
  );
}
