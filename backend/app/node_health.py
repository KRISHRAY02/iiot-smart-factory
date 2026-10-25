import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

import yaml

from app import alerts_db, assets_db, node_health_db, rules
from app.config import settings
from app.models import Alert
from app.ws_manager import manager

log = logging.getLogger("node_health")

_lock = threading.Lock()
_last_seen: dict[str, datetime] = {}
_state: dict[str, str] = {}
_offline_alert_ids: dict[str, str] = {}
_node_configs: dict[str, dict] = {}
_default_interval = 5
_cfg = {
    "stale_multiplier": settings.node_health_stale_multiplier,
    "offline_multiplier": settings.node_health_offline_multiplier,
    "check_interval_seconds": settings.node_health_check_interval_seconds,
}

_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None


def _load_node_configs():
    global _node_configs, _default_interval
    try:
        with open(settings.sensor_nodes_config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except OSError as exc:
        log.warning("Could not load sensor-nodes config (%s) for health intervals: %s", settings.sensor_nodes_config_path, exc)
        cfg = {}
    _default_interval = cfg.get("publish_interval_seconds", 5)
    _node_configs = {n["id"]: n for n in cfg.get("nodes", [])}


def publish_interval_for(node_id: str) -> float:
    node_cfg = _node_configs.get(node_id, {})
    return float(node_cfg.get("publish_interval_seconds", _default_interval))


def known_node_ids() -> list[str]:
    return sorted(_node_configs.keys())


def node_unit(node_id: str) -> Optional[str]:
    return _node_configs.get(node_id, {}).get("unit")


def record_seen(node_id: str, when: Optional[datetime] = None):
    when = when or datetime.now(timezone.utc)
    with _lock:
        _last_seen[node_id] = when
    try:
        node_health_db.record_seen(node_id, when.isoformat())
    except Exception as exc:
        log.error("Failed to persist last_seen for %s: %s", node_id, exc)


def _seconds_since_seen(node_id: str, now: datetime) -> Optional[float]:
    with _lock:
        last = _last_seen.get(node_id)
    if last is None:
        return None
    return (now - last).total_seconds()


def compute_state(seconds_since_seen: Optional[float], interval: float, cfg: Optional[dict] = None) -> str:
    """Pure function of elapsed time vs. publish interval — kept standalone
    so the online/stale/offline thresholds are easy to unit test."""
    cfg = cfg or _cfg
    if seconds_since_seen is None:
        return "offline"
    if seconds_since_seen <= interval * cfg["stale_multiplier"]:
        return "online"
    if seconds_since_seen <= interval * cfg["offline_multiplier"]:
        return "stale"
    return "offline"


def _state_for_node(node_id: str, now: datetime) -> str:
    seconds = _seconds_since_seen(node_id, now)
    interval = publish_interval_for(node_id)
    return compute_state(seconds, interval)


def snapshot() -> list[dict]:
    now = datetime.now(timezone.utc)
    with _lock:
        last_seen_copy = dict(_last_seen)
    rows = []
    for node_id in known_node_ids():
        last = last_seen_copy.get(node_id)
        seconds = (now - last).total_seconds() if last else None
        asset = assets_db.find_asset_for_node(node_id)
        rows.append(
            {
                "node_id": node_id,
                "asset_name": asset.name if asset else None,
                "sensor_type": _node_configs.get(node_id, {}).get("type"),
                "state": _state.get(node_id, "offline"),
                "last_seen": last.isoformat() if last else None,
                "seconds_since_last_seen": seconds,
            }
        )
    return rows


def _handle_transition(node_id: str, old_state: Optional[str], new_state: str):
    asset = assets_db.find_asset_for_node(node_id)
    under_maintenance = asset is not None and asset.status == "Under Maintenance"

    if new_state == "offline" and old_state != "offline":
        if node_id in _offline_alert_ids:
            return
        sensor_type = _node_configs.get(node_id, {}).get("type", "unknown")
        alert = Alert(
            id=str(uuid.uuid4()),
            node_id=node_id,
            asset_id=asset.asset_id if asset else None,
            sensor_type=sensor_type,
            value=0.0,
            threshold=0.0,
            condition="offline",
            severity="info",
            message=f"Node {node_id} stopped publishing",
            timestamp=datetime.now(timezone.utc).isoformat(),
            alert_type="node_offline",
        )
        auto_resolved_reason = "Suppressed — asset under maintenance" if under_maintenance else None
        try:
            record = alerts_db.create_alert(alert, auto_resolved_reason=auto_resolved_reason)
        except Exception as exc:
            log.error("Failed to write node_offline alert for %s: %s", node_id, exc)
            return

        if under_maintenance:
            log.info("NODE OFFLINE SUPPRESSED [%s] (asset under maintenance)", node_id)
            return

        _offline_alert_ids[node_id] = record.id
        log.warning("NODE OFFLINE [%s]", node_id)
        manager.broadcast_threadsafe({"type": "alert", "data": record.model_dump()})

    elif old_state == "offline" and new_state != "offline":
        alert_id = _offline_alert_ids.pop(node_id, None)
        if alert_id is None:
            return
        record = alerts_db.resolve_alert(alert_id, "system", resolution_note="Node resumed publishing")
        if record is not None:
            log.info("NODE RECOVERED [%s]", node_id)
            manager.broadcast_threadsafe({"type": "alert", "data": record.model_dump()})


def _poll_once():
    now = datetime.now(timezone.utc)
    changed = False
    for node_id in known_node_ids():
        new_state = _state_for_node(node_id, now)
        old_state = _state.get(node_id)
        if old_state != new_state:
            _state[node_id] = new_state
            changed = True
            _handle_transition(node_id, old_state, new_state)
    if changed:
        manager.broadcast_threadsafe({"type": "node_health", "data": snapshot()})


def _rehydrate():
    now = datetime.now(timezone.utc)
    try:
        persisted = node_health_db.load_all()
    except Exception as exc:
        log.error("Failed to load persisted node health state: %s", exc)
        persisted = {}
    with _lock:
        for node_id, iso in persisted.items():
            try:
                _last_seen[node_id] = datetime.fromisoformat(iso)
            except ValueError:
                continue
    for node_id in known_node_ids():
        _state[node_id] = _state_for_node(node_id, now)


def _run_loop():
    while not _stop_event.is_set():
        try:
            _poll_once()
        except Exception:
            log.exception("Node health poll iteration failed")
        _stop_event.wait(_cfg["check_interval_seconds"])


def start():
    global _thread, _cfg
    _load_node_configs()
    _cfg = rules.load_node_health_config()
    _rehydrate()
    _stop_event.clear()
    _thread = threading.Thread(target=_run_loop, name="node-health", daemon=True)
    _thread.start()


def stop():
    _stop_event.set()
    if _thread is not None:
        _thread.join(timeout=2)
