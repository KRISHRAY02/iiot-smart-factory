import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchHistory, fetchNodes } from "../lib/api";

const UNITS = {
  temperature: "°C",
  pressure: "kPa",
  vibration: "mm/s",
  humidity: "%RH",
};

export default function HistoryChart({ refreshKey, nodeOptions }) {
  const [nodes, setNodes] = useState(nodeOptions || []);
  const [selectedNode, setSelectedNode] = useState(nodeOptions?.[0] || "");
  const [hours, setHours] = useState(1);
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (nodeOptions) {
      setNodes(nodeOptions);
      if (!nodeOptions.includes(selectedNode)) {
        setSelectedNode(nodeOptions[0] || "");
      }
      return;
    }
    fetchNodes()
      .then((res) => {
        setNodes(res.nodes);
        if (!selectedNode && res.nodes.length > 0) {
          setSelectedNode(res.nodes[0]);
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
        const history = await fetchHistory({ nodeId: selectedNode, hours });
        if (!cancelled) {
          setError(null);
          setData(
            history.map((h) => {
              const hasBand = h.rolling_mean != null && h.rolling_stddev != null;
              return {
                time: new Date(h.timestamp).toLocaleTimeString(),
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
        // will retry on next interval
      }
    }

    load();
    const id = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [selectedNode, hours, refreshKey]);

  const unit = UNITS[data[0]?.sensorType] || "";

  return (
    <div>
      <div className="history-controls">
        <select value={selectedNode} onChange={(e) => setSelectedNode(e.target.value)}>
          {nodes.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <select value={hours} onChange={(e) => setHours(Number(e.target.value))}>
          <option value={1}>Last 1h</option>
          <option value={6}>Last 6h</option>
          <option value={24}>Last 24h</option>
        </select>
      </div>
      {error ? (
        <div className="history-error">{error}</div>
      ) : data.length === 0 ? (
        <div className="empty-state">No historical data yet for this node.</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data} margin={{ top: 4, right: 12, left: 4, bottom: 12 }}>
            <defs>
              <linearGradient id="historyFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0b5ed7" stopOpacity={0.32} />
                <stop offset="100%" stopColor="#0b5ed7" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={30} />
            <YAxis
              tick={{ fontSize: 11 }}
              label={
                unit
                  ? { value: unit, angle: -90, position: "insideLeft", className: "axis-label" }
                  : undefined
              }
            />
            <Tooltip
              formatter={(value, name) => {
                if (name === "value") return [`${value} ${unit}`, "value"];
                return undefined;
              }}
            />
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
              fill="#0b5ed7"
              fillOpacity={0.12}
              isAnimationActive={false}
              legendType="none"
              tooltipType="none"
              name="normal range"
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#0b5ed7"
              strokeWidth={2}
              fill="url(#historyFill)"
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
      {data.length > 0 && !error && (
        <div className="chart-caption">
          <span className="chart-caption-swatch" /> shaded band = normal range (rolling mean ± 2σ)
        </div>
      )}
    </div>
  );
}
