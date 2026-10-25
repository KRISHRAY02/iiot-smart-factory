import { useState } from "react";
import { triggerAnomaly, triggerOffline } from "../lib/api";

export default function DemoControlsPanel({ nodeIds, nodeLabel }) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(nodeIds[0] || "");
  const [busy, setBusy] = useState(false);

  const activeNode = nodeIds.includes(selected) ? selected : nodeIds[0] || "";

  async function run(action) {
    if (!activeNode) return;
    setBusy(true);
    try {
      if (action === "spike") await triggerAnomaly(activeNode, "spike");
      else if (action === "drift") await triggerAnomaly(activeNode, "drift");
      else if (action === "offline") await triggerOffline(activeNode, "go_offline", 30);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="demo-controls">
      <button
        className="demo-controls-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        title="Controls for demoing anomaly detection and node-offline handling"
      >
        <span aria-hidden="true">🧪</span> Demo controls
        <span className={`chevron ${open ? "open" : ""}`} aria-hidden="true">
          ▾
        </span>
      </button>
      {open && (
        <div className="demo-controls-body">
          <select
            className="demo-controls-select"
            value={activeNode}
            onChange={(e) => setSelected(e.target.value)}
            disabled={nodeIds.length === 0}
          >
            {nodeIds.map((n) => (
              <option key={n} value={n}>
                {nodeLabel?.[n] || n}
              </option>
            ))}
          </select>
          <div className="demo-control-row">
            <button className="trigger-btn" disabled={busy || !activeNode} onClick={() => run("spike")}>
              ⚡ Spike
            </button>
            <span className="demo-control-desc">Sudden jump past the hard limit</span>
          </div>
          <div className="demo-control-row">
            <button className="trigger-btn drift" disabled={busy || !activeNode} onClick={() => run("drift")}>
              📉 Drift
            </button>
            <span className="demo-control-desc">Gradual shift outside normal range</span>
          </div>
          <div className="demo-control-row">
            <button className="trigger-btn offline" disabled={busy || !activeNode} onClick={() => run("offline")}>
              📡 Go offline
            </button>
            <span className="demo-control-desc">Stop publishing for 30s</span>
          </div>
        </div>
      )}
    </div>
  );
}
