import { useState } from "react";
import { exportAlertsCsv, exportReadingsCsv } from "../lib/api";

const RANGE_PRESETS = [
  { value: "1h", label: "Last 1h" },
  { value: "6h", label: "Last 6h" },
  { value: "24h", label: "Last 24h" },
  { value: "7d", label: "Last 7d" },
  { value: "custom", label: "Custom" },
];

const SEVERITY_OPTIONS = ["", "critical", "warning", "info"];

function presetRange(preset) {
  const end = new Date();
  const start = new Date(end);
  if (preset === "1h") start.setHours(start.getHours() - 1);
  else if (preset === "6h") start.setHours(start.getHours() - 6);
  else if (preset === "24h") start.setDate(start.getDate() - 1);
  else if (preset === "7d") start.setDate(start.getDate() - 7);
  return { start, end };
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ExportPanel({ assets = [], defaultKind = "readings" }) {
  const [kind, setKind] = useState(defaultKind);
  const [preset, setPreset] = useState("1h");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [assetId, setAssetId] = useState("");
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function resolveRange() {
    if (preset !== "custom") return presetRange(preset);
    if (!customStart || !customEnd) {
      throw new Error("Pick both a start and end date/time for a custom range");
    }
    const start = new Date(customStart);
    const end = new Date(customEnd);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      throw new Error("Invalid custom date/time");
    }
    return { start, end };
  }

  async function handleDownload() {
    setError(null);
    setLoading(true);
    try {
      const { start, end } = resolveRange();
      const params = { start: start.toISOString(), end: end.toISOString() };
      if (assetId) params.asset_id = assetId;

      const result =
        kind === "readings"
          ? await exportReadingsCsv(params)
          : await exportAlertsCsv(severity ? { ...params, severity } : params);

      triggerDownload(result.blob, result.filename);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="history-filters">
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="readings">Readings</option>
          <option value="alerts">Alerts</option>
        </select>
        <select value={preset} onChange={(e) => setPreset(e.target.value)}>
          {RANGE_PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        {preset === "custom" && (
          <>
            <input
              type="datetime-local"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              title="From"
            />
            <input
              type="datetime-local"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              title="To"
            />
          </>
        )}
        <select value={assetId} onChange={(e) => setAssetId(e.target.value)}>
          <option value="">All assets</option>
          {assets.map((a) => (
            <option key={a.asset_id} value={a.asset_id}>
              {a.name}
            </option>
          ))}
        </select>
        {kind === "alerts" && (
          <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
            {SEVERITY_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s ? s[0].toUpperCase() + s.slice(1) : "All severities"}
              </option>
            ))}
          </select>
        )}
        <button className="alert-btn ack" disabled={loading} onClick={handleDownload}>
          {loading ? "Preparing…" : "Download CSV"}
        </button>
      </div>
      {error && <div className="history-error">{error}</div>}
    </div>
  );
}
