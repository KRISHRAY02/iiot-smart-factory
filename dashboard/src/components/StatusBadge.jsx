const STATUS_CLASS = {
  Operational: "status-badge-ok",
  "Under Maintenance": "status-badge-warn",
  Offline: "status-badge-danger",
  Decommissioned: "status-badge-gray",
};

export default function StatusBadge({ status }) {
  return <span className={`status-badge ${STATUS_CLASS[status] || "status-badge-gray"}`}>{status}</span>;
}
