import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.models import Alert, AlertRecord

log = logging.getLogger("alerts_db")

_conn: Optional[sqlite3.Connection] = None


def connect():
    global _conn
    os.makedirs(os.path.dirname(settings.assets_db_path), exist_ok=True)
    _conn = sqlite3.connect(settings.assets_db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            asset_id TEXT,
            sensor_type TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            value REAL NOT NULL,
            threshold REAL,
            condition TEXT,
            message TEXT NOT NULL,
            z_score REAL,
            baseline_mean REAL,
            baseline_stddev REAL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            acknowledged_at TEXT,
            acknowledged_by TEXT,
            resolved_at TEXT,
            resolved_by TEXT,
            resolution_note TEXT
        )
        """
    )
    _conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")
    _conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_asset ON alerts(asset_id)")
    _conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at)")
    _conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_record(row: sqlite3.Row) -> AlertRecord:
    return AlertRecord(
        id=row["id"],
        node_id=row["node_id"],
        asset_id=row["asset_id"],
        sensor_type=row["sensor_type"],
        alert_type=row["alert_type"],
        severity=row["severity"],
        value=row["value"],
        threshold=row["threshold"],
        condition=row["condition"],
        message=row["message"],
        z_score=row["z_score"],
        baseline_mean=row["baseline_mean"],
        baseline_stddev=row["baseline_stddev"],
        status=row["status"],
        created_at=row["created_at"],
        acknowledged_at=row["acknowledged_at"],
        acknowledged_by=row["acknowledged_by"],
        resolved_at=row["resolved_at"],
        resolved_by=row["resolved_by"],
        resolution_note=row["resolution_note"],
    )


def create_alert(alert: Alert, auto_resolved_reason: Optional[str] = None) -> AlertRecord:
    """Insert a newly-fired alert. If `auto_resolved_reason` is given (e.g. the
    owning asset is under maintenance), the alert is stored already resolved
    by "system" so it never shows up as active but still appears in history."""
    alert_id = alert.id or str(uuid.uuid4())
    now = _now()
    status = "resolved" if auto_resolved_reason else "active"
    resolved_at = now if auto_resolved_reason else None
    resolved_by = "system" if auto_resolved_reason else None

    _conn.execute(
        """
        INSERT INTO alerts (
            id, node_id, asset_id, sensor_type, alert_type, severity, value,
            threshold, condition, message, z_score, baseline_mean, baseline_stddev,
            status, created_at, resolved_at, resolved_by, resolution_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            alert_id,
            alert.node_id,
            alert.asset_id,
            alert.sensor_type,
            alert.alert_type,
            alert.severity,
            alert.value,
            alert.threshold,
            alert.condition,
            alert.message,
            alert.z_score,
            alert.baseline_mean,
            alert.baseline_stddev,
            status,
            alert.timestamp or now,
            resolved_at,
            resolved_by,
            auto_resolved_reason,
        ),
    )
    _conn.commit()
    return get_alert(alert_id)


def get_alert(alert_id: str) -> Optional[AlertRecord]:
    row = _conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    return _row_to_record(row) if row else None


def acknowledge_alert(alert_id: str, user: str) -> Optional[AlertRecord]:
    alert = get_alert(alert_id)
    if alert is None or alert.status != "active":
        return None
    now = _now()
    _conn.execute(
        "UPDATE alerts SET status = 'acknowledged', acknowledged_at = ?, acknowledged_by = ? WHERE id = ?",
        (now, user, alert_id),
    )
    _conn.commit()
    return get_alert(alert_id)


def resolve_alert(alert_id: str, user: str, resolution_note: Optional[str] = None) -> Optional[AlertRecord]:
    alert = get_alert(alert_id)
    if alert is None or alert.status not in ("active", "acknowledged"):
        return None
    now = _now()
    _conn.execute(
        "UPDATE alerts SET status = 'resolved', resolved_at = ?, resolved_by = ?, resolution_note = ? WHERE id = ?",
        (now, user, resolution_note, alert_id),
    )
    _conn.commit()
    return get_alert(alert_id)


def list_open(asset_id: Optional[str] = None) -> list[AlertRecord]:
    """Alerts still visible in the Active panel: active or acknowledged."""
    query = "SELECT * FROM alerts WHERE status != 'resolved'"
    params: list = []
    if asset_id:
        query += " AND asset_id = ?"
        params.append(asset_id)
    query += " ORDER BY created_at DESC"
    rows = _conn.execute(query, params).fetchall()
    return [_row_to_record(r) for r in rows]


def _history_where(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    asset_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> tuple[str, list]:
    clauses = ["1=1"]
    params: list = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if asset_id:
        clauses.append("asset_id = ?")
        params.append(asset_id)
    if start:
        clauses.append("created_at >= ?")
        params.append(start)
    if end:
        clauses.append("created_at <= ?")
        params.append(end)
    return " AND ".join(clauses), params


def list_history(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    asset_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 200,
) -> list[AlertRecord]:
    where, params = _history_where(status, severity, asset_id, start, end)
    rows = _conn.execute(
        f"SELECT * FROM alerts WHERE {where} ORDER BY created_at DESC LIMIT ?", params + [limit]
    ).fetchall()
    return [_row_to_record(r) for r in rows]


def count_history(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    asset_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> int:
    where, params = _history_where(status, severity, asset_id, start, end)
    row = _conn.execute(f"SELECT COUNT(*) AS c FROM alerts WHERE {where}", params).fetchone()
    return row["c"]


def stream_history(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    asset_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    chunk_size: int = 500,
):
    """Yields AlertRecords lazily off a server-side cursor, for CSV export
    without materializing the whole result set in memory."""
    where, params = _history_where(status, severity, asset_id, start, end)
    cursor = _conn.execute(f"SELECT * FROM alerts WHERE {where} ORDER BY created_at ASC", params)
    while True:
        rows = cursor.fetchmany(chunk_size)
        if not rows:
            break
        for row in rows:
            yield _row_to_record(row)


def summary_stats() -> dict:
    active_rows = _conn.execute(
        "SELECT severity, COUNT(*) AS c FROM alerts WHERE status = 'active' GROUP BY severity"
    ).fetchall()
    active_by_severity = {"critical": 0, "warning": 0, "info": 0}
    for row in active_rows:
        active_by_severity[row["severity"]] = row["c"]

    ack_rows = _conn.execute(
        "SELECT created_at, acknowledged_at FROM alerts WHERE acknowledged_at IS NOT NULL"
    ).fetchall()
    avg_ack = _avg_seconds_between(ack_rows, "created_at", "acknowledged_at")

    resolve_rows = _conn.execute(
        "SELECT created_at, resolved_at FROM alerts WHERE resolved_at IS NOT NULL AND resolved_by != 'system'"
    ).fetchall()
    avg_resolve = _avg_seconds_between(resolve_rows, "created_at", "resolved_at")

    return {
        "active_by_severity": active_by_severity,
        "avg_time_to_acknowledge_seconds": avg_ack,
        "avg_time_to_resolve_seconds": avg_resolve,
    }


def _avg_seconds_between(rows: list[sqlite3.Row], start_key: str, end_key: str) -> Optional[float]:
    if not rows:
        return None
    deltas = []
    for row in rows:
        try:
            start = datetime.fromisoformat(row[start_key])
            end = datetime.fromisoformat(row[end_key])
        except (ValueError, TypeError):
            continue
        deltas.append((end - start).total_seconds())
    if not deltas:
        return None
    return sum(deltas) / len(deltas)
