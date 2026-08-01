import { triggerAnomaly } from "../lib/api";

export default function LiveReadings({ readings }) {
  const nodes = Object.values(readings).sort((a, b) => a.node_id.localeCompare(b.node_id));

  if (nodes.length === 0) {
    return <div className="empty-state">Waiting for sensor data...</div>;
  }

  return (
    <>
      {nodes.map((r) => (
        <div className="reading-row" key={r.node_id}>
          <div>
            <div className="reading-node">{r.node_id}</div>
            <div className="reading-type">{r.sensor_type}</div>
          </div>
          <div className={`reading-value ${r.anomaly ? "anomaly" : ""}`}>
            {r.value} {r.unit}
          </div>
          <button className="trigger-btn" onClick={() => triggerAnomaly(r.node_id)}>
            Trigger anomaly
          </button>
        </div>
      ))}
    </>
  );
}
