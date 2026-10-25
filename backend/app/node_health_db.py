import os
import sqlite3
from typing import Optional

from app.config import settings

_conn: Optional[sqlite3.Connection] = None


def connect():
    """Shares the sqlite file used by assets_db/alerts_db — a separate table,
    not a separate database."""
    global _conn
    os.makedirs(os.path.dirname(settings.assets_db_path), exist_ok=True)
    _conn = sqlite3.connect(settings.assets_db_path, check_same_thread=False)
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS node_health (
            node_id TEXT PRIMARY KEY,
            last_seen TEXT NOT NULL
        )
        """
    )
    _conn.commit()


def record_seen(node_id: str, last_seen_iso: str):
    _conn.execute(
        """
        INSERT INTO node_health (node_id, last_seen) VALUES (?, ?)
        ON CONFLICT(node_id) DO UPDATE SET last_seen = excluded.last_seen
        """,
        (node_id, last_seen_iso),
    )
    _conn.commit()


def load_all() -> dict[str, str]:
    """node_id -> last_seen ISO timestamp, used to rehydrate in-memory state
    on backend startup so a restart doesn't mark every node offline until
    its next reading arrives."""
    rows = _conn.execute("SELECT node_id, last_seen FROM node_health").fetchall()
    return {row[0]: row[1] for row in rows}
