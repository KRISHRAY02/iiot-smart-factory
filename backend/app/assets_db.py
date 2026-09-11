import json
import logging
import os
import sqlite3
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from app.config import settings
from app.models import Asset, AssetCreate, AssetUpdate

log = logging.getLogger("assets_db")

_conn: Optional[sqlite3.Connection] = None


def connect():
    global _conn
    os.makedirs(os.path.dirname(settings.assets_db_path), exist_ok=True)
    _conn = sqlite3.connect(settings.assets_db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            model_number TEXT,
            manufacturer TEXT,
            install_date TEXT,
            last_maintenance_date TEXT,
            next_scheduled_maintenance TEXT,
            status TEXT NOT NULL DEFAULT 'Operational',
            location TEXT,
            linked_sensor_nodes TEXT NOT NULL DEFAULT '[]',
            deleted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    _conn.commit()
    _seed_if_empty()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_asset(row: sqlite3.Row) -> Asset:
    next_maint = row["next_scheduled_maintenance"]
    overdue = False
    if next_maint and row["status"] not in ("Decommissioned",):
        try:
            overdue = date.fromisoformat(next_maint) < datetime.now(timezone.utc).date()
        except ValueError:
            overdue = False
    return Asset(
        asset_id=row["asset_id"],
        name=row["name"],
        asset_type=row["asset_type"],
        model_number=row["model_number"],
        manufacturer=row["manufacturer"],
        install_date=row["install_date"],
        last_maintenance_date=row["last_maintenance_date"],
        next_scheduled_maintenance=row["next_scheduled_maintenance"],
        status=row["status"],
        location=row["location"],
        linked_sensor_nodes=json.loads(row["linked_sensor_nodes"]),
        maintenance_overdue=overdue,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_assets(include_deleted: bool = False) -> list[Asset]:
    query = "SELECT * FROM assets"
    if not include_deleted:
        query += " WHERE deleted = 0"
    query += " ORDER BY name"
    rows = _conn.execute(query).fetchall()
    return [_row_to_asset(r) for r in rows]


def get_asset(asset_id: str, include_deleted: bool = False) -> Optional[Asset]:
    row = _conn.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    if row is None:
        return None
    if not include_deleted and row["deleted"]:
        return None
    return _row_to_asset(row)


def create_asset(data: AssetCreate) -> Asset:
    asset_id = data.asset_id or str(uuid.uuid4())
    now = _now()
    _conn.execute(
        """
        INSERT INTO assets (
            asset_id, name, asset_type, model_number, manufacturer, install_date,
            last_maintenance_date, next_scheduled_maintenance, status, location,
            linked_sensor_nodes, deleted, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            asset_id,
            data.name,
            data.asset_type,
            data.model_number,
            data.manufacturer,
            data.install_date,
            data.last_maintenance_date,
            data.next_scheduled_maintenance,
            data.status,
            data.location,
            json.dumps(data.linked_sensor_nodes),
            now,
            now,
        ),
    )
    _conn.commit()
    return get_asset(asset_id)


def update_asset(asset_id: str, data: AssetUpdate) -> Optional[Asset]:
    existing = get_asset(asset_id)
    if existing is None:
        return None

    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return existing

    set_clauses = []
    values = []
    for key, value in fields.items():
        if key == "linked_sensor_nodes":
            value = json.dumps(value)
        set_clauses.append(f"{key} = ?")
        values.append(value)
    set_clauses.append("updated_at = ?")
    values.append(_now())
    values.append(asset_id)

    _conn.execute(f"UPDATE assets SET {', '.join(set_clauses)} WHERE asset_id = ?", values)
    _conn.commit()
    return get_asset(asset_id)


def soft_delete_asset(asset_id: str) -> bool:
    cur = _conn.execute(
        "UPDATE assets SET deleted = 1, updated_at = ? WHERE asset_id = ? AND deleted = 0",
        (_now(), asset_id),
    )
    _conn.commit()
    return cur.rowcount > 0


def find_asset_for_node(node_id: str) -> Optional[Asset]:
    for asset in list_assets():
        if node_id in asset.linked_sensor_nodes:
            return asset
    return None


_SEED_ASSETS = [
    {
        "asset_id": "asset-press-line1",
        "name": "Hydraulic Press - Line 1",
        "asset_type": "Press",
        "model_number": "HP-4400X",
        "manufacturer": "Schuler",
        "install_date": "2022-03-14",
        "last_maintenance_date": "2026-07-01",
        "next_scheduled_maintenance": "2026-10-01",
        "status": "Operational",
        "location": "Line 1, Bay 1",
        "linked_sensor_nodes": ["press-line1", "temp-line1"],
    },
    {
        "asset_id": "asset-conveyor-line1",
        "name": "Main Conveyor - Line 1",
        "asset_type": "Conveyor",
        "model_number": "CV-220",
        "manufacturer": "Dorner",
        "install_date": "2021-11-02",
        "last_maintenance_date": "2026-06-15",
        "next_scheduled_maintenance": "2026-08-15",
        "status": "Operational",
        "location": "Line 1, Bay 2",
        "linked_sensor_nodes": ["vib-line1"],
    },
    {
        "asset_id": "asset-hvac-line1",
        "name": "Climate Control Unit - Line 1",
        "asset_type": "HVAC",
        "model_number": "CCU-9",
        "manufacturer": "Carrier",
        "install_date": "2023-01-20",
        "last_maintenance_date": "2026-05-10",
        "next_scheduled_maintenance": "2026-11-10",
        "status": "Operational",
        "location": "Line 1, Bay 3",
        "linked_sensor_nodes": ["hum-line1"],
    },
    {
        "asset_id": "asset-compressor-bay4",
        "name": "Legacy Air Compressor - Bay 4",
        "asset_type": "Compressor",
        "model_number": "AC-100",
        "manufacturer": "Atlas Copco",
        "install_date": "2016-09-05",
        "last_maintenance_date": "2025-12-01",
        "next_scheduled_maintenance": "2026-06-01",
        "status": "Decommissioned",
        "location": "Bay 4 (retired)",
        "linked_sensor_nodes": [],
    },
]


def _seed_if_empty():
    count = _conn.execute("SELECT COUNT(*) AS c FROM assets").fetchone()["c"]
    if count > 0:
        return
    log.info("Seeding assets table with sample data")
    now = _now()
    for seed in _SEED_ASSETS:
        _conn.execute(
            """
            INSERT INTO assets (
                asset_id, name, asset_type, model_number, manufacturer, install_date,
                last_maintenance_date, next_scheduled_maintenance, status, location,
                linked_sensor_nodes, deleted, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                seed["asset_id"],
                seed["name"],
                seed["asset_type"],
                seed["model_number"],
                seed["manufacturer"],
                seed["install_date"],
                seed["last_maintenance_date"],
                seed["next_scheduled_maintenance"],
                seed["status"],
                seed["location"],
                json.dumps(seed["linked_sensor_nodes"]),
                now,
                now,
            ),
        )
    _conn.commit()
