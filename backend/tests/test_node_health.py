from datetime import datetime, timedelta, timezone

from app import node_health

CFG = {"stale_multiplier": 2.0, "offline_multiplier": 4.0}


def test_compute_state_online_within_stale_multiplier():
    assert node_health.compute_state(0, 5, CFG) == "online"
    assert node_health.compute_state(10, 5, CFG) == "online"  # exactly 2x interval


def test_compute_state_stale_between_multipliers():
    assert node_health.compute_state(10.1, 5, CFG) == "stale"
    assert node_health.compute_state(20, 5, CFG) == "stale"  # exactly 4x interval


def test_compute_state_offline_beyond_offline_multiplier():
    assert node_health.compute_state(20.1, 5, CFG) == "offline"
    assert node_health.compute_state(1000, 5, CFG) == "offline"


def test_compute_state_offline_when_never_seen():
    assert node_health.compute_state(None, 5, CFG) == "offline"


def _reset_node(node_id, node_cfg):
    node_health._node_configs.clear()
    node_health._node_configs[node_id] = node_cfg
    node_health._state.clear()
    node_health._offline_alert_ids.clear()
    node_health._last_seen.clear()


def test_offline_alert_fires_once_and_resolves_on_recovery(fresh_db, monkeypatch):
    from app import alerts_db

    monkeypatch.setattr(node_health.manager, "broadcast_threadsafe", lambda *_: None)
    _reset_node("node-a", {"id": "node-a", "type": "temperature", "unit": "C", "publish_interval_seconds": 5})

    now = datetime.now(timezone.utc)
    node_health._last_seen["node-a"] = now - timedelta(seconds=100)
    node_health._state["node-a"] = "online"

    node_health._poll_once()
    assert node_health._state["node-a"] == "offline"

    def open_offline_alerts():
        return [a for a in alerts_db.list_open() if a.alert_type == "node_offline" and a.node_id == "node-a"]

    assert len(open_offline_alerts()) == 1

    # Staying offline on a later poll must not raise a duplicate alert.
    node_health._poll_once()
    assert len(open_offline_alerts()) == 1

    # Coming back online auto-resolves it as "system".
    node_health.record_seen("node-a", when=datetime.now(timezone.utc))
    node_health._poll_once()
    assert node_health._state["node-a"] == "online"
    assert open_offline_alerts() == []

    history = [a for a in alerts_db.list_history() if a.alert_type == "node_offline" and a.node_id == "node-a"]
    assert len(history) == 1
    assert history[0].status == "resolved"
    assert history[0].resolved_by == "system"
    assert history[0].resolution_note == "Node resumed publishing"


def test_offline_alert_suppressed_under_maintenance(fresh_db, monkeypatch):
    from app import alerts_db, assets_db
    from app.models import AssetCreate

    assets_db.create_asset(
        AssetCreate(name="Press", asset_type="Press", status="Under Maintenance", linked_sensor_nodes=["node-b"])
    )
    monkeypatch.setattr(node_health.manager, "broadcast_threadsafe", lambda *_: None)
    _reset_node("node-b", {"id": "node-b", "type": "vibration", "unit": "mm/s", "publish_interval_seconds": 5})

    now = datetime.now(timezone.utc)
    node_health._last_seen["node-b"] = now - timedelta(seconds=100)
    node_health._state["node-b"] = "online"

    node_health._poll_once()

    assert node_health._state["node-b"] == "offline"
    assert alerts_db.list_open() == []  # suppressed, not left active

    history = [a for a in alerts_db.list_history() if a.alert_type == "node_offline" and a.node_id == "node-b"]
    assert len(history) == 1
    assert history[0].status == "resolved"
    assert history[0].resolved_by == "system"
    assert "maintenance" in history[0].resolution_note.lower()
