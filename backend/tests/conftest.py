import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("SENSOR_NODES_CONFIG_PATH", str(BACKEND_DIR.parent / "sensor-nodes" / "config.yaml"))
os.environ.setdefault("RULES_CONFIG_PATH", str(BACKEND_DIR / "rules.yaml"))


@pytest.fixture(autouse=True, scope="session")
def _load_node_configs_once():
    from app import node_health

    node_health._load_node_configs()


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Points the shared sqlite file (assets/alerts/node_health tables) at a
    throwaway path for this test and (re)connects each module to it."""
    from app import alerts_db, assets_db, node_health_db
    from app.config import settings

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(settings, "assets_db_path", db_path)
    assets_db.connect()
    alerts_db.connect()
    node_health_db.connect()
    return db_path
