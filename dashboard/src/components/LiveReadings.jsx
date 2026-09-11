import { triggerAnomaly } from "../lib/api";
import { iconFor } from "../lib/sensorIcons";

export default function LiveReadings({ readings, assetsByNode }) {
  const nodes = Object.values(readings).sort((a, b) => a.node_id.localeCompare(b.node_id));

  if (nodes.length === 0) {
    return <div className="empty-state">Waiting for sensor data...</div>;
  }

  return (
    <>
      {nodes.map((r) => {
        const asset = assetsByNode?.[r.node_id];
        const hasBand = r.rolling_mean != null && r.rolling_stddev != null;
        const bandLower = hasBand ? r.rolling_mean - 2 * r.rolling_stddev : null;
        const bandUpper = hasBand ? r.rolling_mean + 2 * r.rolling_stddev : null;
        const outsideBand = hasBand && (r.value < bandLower || r.value > bandUpper);
        return (
          <div className={`reading-row ${r.anomaly ? "anomaly" : ""}`} key={r.node_id}>
            <div className="reading-main">
              <span className="reading-icon" aria-hidden="true">
                {iconFor(r.sensor_type)}
              </span>
              <div className="reading-labels">
                <div className="reading-node" title={asset ? `${asset.name} · ${r.sensor_type}` : r.node_id}>
                  {asset ? `${asset.name} · ${r.sensor_type}` : r.node_id}
                </div>
                <div className="reading-type">{asset ? asset.location : r.sensor_type}</div>
                {hasBand && (
                  <div className={`reading-band ${outsideBand ? "outside" : ""}`}>
                    Normal: {bandLower.toFixed(1)}–{bandUpper.toFixed(1)} {r.unit}
                  </div>
                )}
              </div>
            </div>
            <div className="reading-actions">
              <div className={`reading-value ${r.anomaly ? "anomaly" : ""}`}>
                {r.value} {r.unit}
              </div>
              <button
                className="trigger-btn"
                title="Spike past the hard static threshold"
                onClick={() => triggerAnomaly(r.node_id, "spike")}
              >
                ⚡ Spike
              </button>
              <button
                className="trigger-btn drift"
                title="Drift a few σ off the statistical baseline without crossing the hard limit"
                onClick={() => triggerAnomaly(r.node_id, "drift")}
              >
                📉 Drift
              </button>
            </div>
          </div>
        );
      })}
    </>
  );
}
