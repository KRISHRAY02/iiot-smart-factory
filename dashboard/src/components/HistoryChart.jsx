import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { fetchHistory, fetchNodes } from "../lib/api";

const UNITS = {
  temperature: "°C",
  pressure: "kPa",
  vibration: "mm/s",
  humidity: "%RH",
};

const RANGES = [
  { value: "5m", label: "5m", hours: 1, windowMs: 5 * 60 * 1000 },
  { value: "1h", label: "1h", hours: 1, windowMs: 60 * 60 * 1000 },
  { value: "6h", label: "6h", hours: 6, windowMs: 6 * 60 * 60 * 1000 },
  { value: "24h", label: "24h", hours: 24, windowMs: 24 * 60 * 60 * 1000 },
];

const SEVERITY_COLOR = { critical: "#d93025", warning: "#e0a100", info: "#51677e" };

function MarkerDot({ cx, cy, payload }) {
  if (cx == null || cy == null) return null;
  const color = SEVERITY_COLOR[payload.severity] || "#51677e";
  return <circle cx={cx} cy={cy} r={4.5} fill={color} stroke="#fff" strokeWidth={1.5} />;
}

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function ChartTooltip({ active, payload, label, unit }) {
  if (!active || !payload?.length) return null;
  const valuePoint = payload.find((p) => p.dataKey === "value");
  const marker = payload.find((p) => p.dataKey === "markerValue" && p.payload?.alertType);
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-time">{formatTime(label)}</div>
      {valuePoint && (
        <div>
          value: {valuePoint.value} {unit}
        </div>
      )}
      {marker && (
        <div className="chart-tooltip-alert" style={{ color: SEVERITY_COLOR[marker.payload.severity] }}>
          ⚠ {marker.payload.alertType} · {marker.payload.severity}
        </div>
      )}
    </div>
  );
}

export default function HistoryChart({
  refreshKey,
  nodeOptions,
  nodeLabel,
  selectedNode: controlledNode,
  onSelectNode,
  alertsForChart,
}) {
  const [nodes, setNodes] = useState(nodeOptions || []);
  const [internalSelected, setInternalSelected] = useState(nodeOptions?.[0] || "");
  const [range, setRange] = useState("1h");
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  const selectedNode = controlledNode !== undefined ? controlledNode : internalSelected;
  const setSelectedNode = onSelectNode || setInternalSelected;
  const rangeCfg = RANGES.find((r) => r.value === range) || RANGES[1];

  useEffect(() => {
    if (nodeOptions) {
      setNodes(nodeOptions);
      if (controlledNode === undefined && !nodeOptions.includes(internalSelected)) {
        setInternalSelected(nodeOptions[0] || "");
      }
      return;
    }
    fetchNodes()
      .then((res) => {
        setNodes(res.nodes);
        if (controlledNode === undefined && !internalSelected && res.nodes.length > 0) {
          setInternalSelected(res.nodes[0]);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, nodeOptions]);

  useEffect(() => {
    if (!selectedNode) return;
    let cancelled = false;

    async function load() {
      try {
        const history = await fetchHistory({ nodeId: selectedNode, hours: rangeCfg.hours });
        if (!cancelled) {
          setError(null);
          setData(
            history.map((h) => {
              const hasBand = h.rolling_mean != null && h.rolling_stddev != null;
              return {
                ts: new Date(h.timestamp).getTime(),
                value: h.value,
                sensorType: h.sensor_type,
                bandLower: hasBand ? h.rolling_mean - 2 * h.rolling_stddev : null,
                bandWidth: hasBand ? 4 * h.rolling_stddev : null,
              };
            })
          );
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    load();
    const id = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [selectedNode, rangeCfg.hours, refreshKey]);

  const windowedData = useMemo(() => {
    if (data.length === 0) return [];
    const latestTs = data[data.length - 1].ts;
    const cutoff = latestTs - rangeCfg.windowMs;
    return data.filter((d) => d.ts >= cutoff);
  }, [data, rangeCfg.windowMs]);

  const domain = useMemo(() => {
    if (windowedData.length === 0) return undefined;
    // Scale to the actual reading values only — the normal-range band can be
    // transiently much wider during baseline warm-up and would otherwise
    // drag the axis down toward 0, flattening the line (the reported bug).
    const values = windowedData.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || Math.max(1, Math.abs(max) * 0.1);
    const pad = span * 0.15;
    return [Math.floor(min - pad), Math.ceil(max + pad)];
  }, [windowedData]);

  const markers = useMemo(() => {
    if (!alertsForChart?.length || windowedData.length === 0) return [];
    return alertsForChart
      .map((alert) => {
        const alertTs = new Date(alert.created_at).getTime();
        let nearest = null;
        let bestDiff = Infinity;
        for (const d of windowedData) {
          const diff = Math.abs(d.ts - alertTs);
          if (diff < bestDiff) {
            bestDiff = diff;
            nearest = d;
          }
        }
        if (!nearest || bestDiff > rangeCfg.windowMs / windowedData.length / 2 + 15000) return null;
        return {
          ts: nearest.ts,
          markerValue: nearest.value,
          severity: alert.severity,
          alertType: alert.alert_type,
        };
      })
      .filter(Boolean);
  }, [alertsForChart, windowedData, rangeCfg.windowMs]);

  const unit = UNITS[windowedData[0]?.sensorType] || "";

  return (
    <div>
      <div className="chart-toolbar">
        <select
          className="chart-node-select"
          value={selectedNode}
          onChange={(e) => setSelectedNode(e.target.value)}
        >
          {nodes.map((n) => (
            <option key={n} value={n}>
              {nodeLabel?.[n] || n}
            </option>
          ))}
        </select>
        <div className="segmented-control" role="group" aria-label="Time range">
          {RANGES.map((r) => (
            <button
              key={r.value}
              className={`segmented-btn ${range === r.value ? "active" : ""}`}
              onClick={() => setRange(r.value)}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div className="history-error">{error}</div>
      ) : windowedData.length === 0 ? (
        <div className="empty-state chart-empty">No historical data yet for this node.</div>
      ) : (
        <ResponsiveContainer width="100%" height={340}>
          <AreaChart data={windowedData} margin={{ top: 8, right: 16, left: 4, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-200)" vertical={false} />
            <XAxis
              dataKey="ts"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={formatTime}
              tick={{ fontSize: 11, fill: "var(--gray-600)" }}
              minTickGap={90}
              axisLine={{ stroke: "var(--gray-200)" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--gray-600)" }}
              domain={domain}
              allowDataOverflow
              axisLine={false}
              tickLine={false}
              width={48}
              label={
                unit
                  ? { value: unit, angle: -90, position: "insideLeft", className: "axis-label" }
                  : undefined
              }
            />
            <Tooltip content={<ChartTooltip unit={unit} />} />
            <Area
              type="monotone"
              dataKey="bandLower"
              stackId="band"
              stroke="none"
              fill="transparent"
              isAnimationActive={false}
              legendType="none"
              tooltipType="none"
            />
            <Area
              type="monotone"
              dataKey="bandWidth"
              stackId="band"
              stroke="none"
              fill="var(--blue-500)"
              fillOpacity={0.14}
              isAnimationActive={false}
              legendType="none"
              tooltipType="none"
              name="normal range"
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--blue-700)"
              strokeWidth={2}
              fill="none"
              dot={false}
              isAnimationActive={false}
            />
            <Scatter data={markers} dataKey="markerValue" xAxisId={0} shape={<MarkerDot />} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      )}
      {windowedData.length > 0 && !error && (
        <div className="chart-caption">
          <span className="chart-caption-swatch" /> shaded band = normal range (rolling mean ± 2σ)
          {markers.length > 0 && (
            <>
              <span className="chart-caption-dot" /> dot = alert moment
            </>
          )}
        </div>
      )}
    </div>
  );
}
