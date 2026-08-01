import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchHistory, fetchNodes } from "../lib/api";

export default function HistoryChart({ refreshKey }) {
  const [nodes, setNodes] = useState([]);
  const [selectedNode, setSelectedNode] = useState("");
  const [hours, setHours] = useState(1);
  const [data, setData] = useState([]);

  useEffect(() => {
    fetchNodes()
      .then((res) => {
        setNodes(res.nodes);
        if (!selectedNode && res.nodes.length > 0) {
          setSelectedNode(res.nodes[0]);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  useEffect(() => {
    if (!selectedNode) return;
    let cancelled = false;

    async function load() {
      try {
        const history = await fetchHistory({ nodeId: selectedNode, hours });
        if (!cancelled) {
          setData(
            history.map((h) => ({
              time: new Date(h.timestamp).toLocaleTimeString(),
              value: h.value,
            }))
          );
        }
      } catch {
        // ignore, will retry on next interval
      }
    }

    load();
    const id = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [selectedNode, hours, refreshKey]);

  return (
    <div>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
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
      {data.length === 0 ? (
        <div className="empty-state">No historical data yet for this node.</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} minTickGap={30} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#1e6fd9" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
