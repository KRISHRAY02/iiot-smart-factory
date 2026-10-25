# Demo script

Covers the two newest features: node health / heartbeat monitoring, and
CSV report export. Assumes the stack is already up
(`docker compose up --build`) and you're logged into the dashboard at
http://localhost:8080.

## 1. Baseline — all nodes online

1. Open the dashboard. Under **Live Sensor Readings**, each node shows a
   green "● Online" dot and a "last seen Ns ago" that keeps ticking down.
2. The **Node Health** summary pill near the top of the dashboard reads
   "4/4 nodes online" in green.

## 2. Take a node offline

1. On any sensor's row, click **📡 Go offline**. This calls
   `POST /api/control/offline/{node_id}`, which publishes a control message
   the simulator subscribes to; the simulator stops publishing for ~30s.
2. Within a few seconds (as last-seen crosses 2× the node's publish
   interval) its health dot turns amber ("Stale"). The reading value is
   still shown, with the health line noting how long ago it was last seen.
3. A few seconds later (past 4× the interval) the dot turns red
   ("Offline"), the reading value is replaced with "No data", and the
   **Node Health** summary pill turns red ("3/4 nodes online · 1 offline").
4. An **info**-severity alert appears in **Active Alerts** under the Info
   group, labeled "Node Offline" with a 🔌 icon.

## 3. Let it resume

1. Either wait ~30s for the simulator's offline window to expire, or click
   **▶ Resume** on that row (now shown in place of "Go offline" while the
   node isn't online) to bring it back immediately.
2. Once a reading arrives, the dot returns to green "Online", the Node
   Health summary returns to "4/4 nodes online", and the "Node Offline"
   alert disappears from Active Alerts — it auto-resolved
   (`resolved_by = "system"`, note "Node resumed publishing").

## 4. Export the offline alert as CSV

1. Go to the **Export** panel (on the dashboard, or the Alert History page).
2. Choose **Alerts**, time range **Last 1h**, and click **Download CSV**.
3. Open the downloaded `alerts_<start>_to_<end>.csv`. The node-offline
   alert is in it, with `alert_type = node_offline`, `severity = info`,
   `status = resolved`, `resolved_by = system`, and
   `resolution_note = Node resumed publishing`.
4. Try **Readings** too, over the same window, to confirm the sensor's
   data gap lines up with the offline period.

## Notes for a live demo

- If you trigger "Go offline" on a node whose asset is **Under
  Maintenance** (see the Assets page), the alert is suppressed — it still
  shows up in Alert History (status `resolved`, note mentions
  maintenance) but never appears in Active Alerts. Good for showing the
  suppression rule works the same way as the other alert types.
- The export range picker caps custom ranges at 7 days and will show a
  clear error (instead of downloading an empty file) if there's no data
  or too many rows for the chosen range/filters.
