import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import yaml

from app.baseline import Baseline
from app.config import settings
from app.models import Alert, SensorReading

log = logging.getLogger("rules")

_ALERT_COOLDOWN_SECONDS = 30
_last_fired: dict[tuple, float] = {}
_last_fired_stat: dict[str, float] = {}


def load_rules():
    with open(settings.rules_config_path, "r") as f:
        return yaml.safe_load(f)["rules"]


def load_node_health_config() -> dict:
    """Node health thresholds, expressed as multiples of each node's publish
    interval. The `node_health:` section of rules.yaml overrides the env/
    settings defaults, so either can be used to tune it."""
    with open(settings.rules_config_path, "r") as f:
        data = yaml.safe_load(f)
    cfg = data.get("node_health") or {}
    return {
        "stale_multiplier": float(cfg.get("stale_multiplier", settings.node_health_stale_multiplier)),
        "offline_multiplier": float(cfg.get("offline_multiplier", settings.node_health_offline_multiplier)),
        "check_interval_seconds": int(cfg.get("check_interval_seconds", settings.node_health_check_interval_seconds)),
    }


_rules = load_rules()


def _condition_met(condition: str, value: float, threshold: float) -> bool:
    if condition == "above":
        return value > threshold
    if condition == "below":
        return value < threshold
    return False


def evaluate(reading: SensorReading) -> Optional[Alert]:
    """Return the highest-severity alert triggered by this reading, if any,
    respecting a per-node/rule cooldown to avoid flooding on repeated
    breaches from the same anomaly episode."""
    matched = []
    for rule in _rules:
        if rule["sensor_type"] != reading.sensor_type:
            continue
        if _condition_met(rule["condition"], reading.value, rule["threshold"]):
            matched.append(rule)

    if not matched:
        return None

    severity_rank = {"critical": 2, "warning": 1}
    matched.sort(key=lambda r: severity_rank.get(r["severity"], 0), reverse=True)
    rule = matched[0]

    key = (reading.node_id, rule["condition"], rule["threshold"])
    now = time.monotonic()
    if now - _last_fired.get(key, 0) < _ALERT_COOLDOWN_SECONDS:
        return None
    _last_fired[key] = now

    return Alert(
        id=str(uuid.uuid4()),
        node_id=reading.node_id,
        sensor_type=reading.sensor_type,
        value=reading.value,
        threshold=rule["threshold"],
        condition=rule["condition"],
        severity=rule["severity"],
        message=rule["message"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        alert_type="threshold_breach",
    )


def evaluate_statistical(reading: SensorReading, stats: Baseline) -> Optional[Alert]:
    """Return a statistical-anomaly alert if this reading deviates from the
    node's own rolling baseline by more than the configured z-score
    threshold. Returns None during cold start (not enough points yet) or
    when the sensor is too stable for a z-score to be meaningful (stats.z_score
    is None in both cases), respecting a per-node cooldown."""
    if stats.z_score is None:
        return None
    if abs(stats.z_score) < settings.stat_z_threshold:
        return None

    now = time.monotonic()
    if now - _last_fired_stat.get(reading.node_id, 0) < settings.stat_alert_cooldown_seconds:
        return None
    _last_fired_stat[reading.node_id] = now

    direction = "above" if stats.z_score > 0 else "below"
    return Alert(
        id=str(uuid.uuid4()),
        node_id=reading.node_id,
        sensor_type=reading.sensor_type,
        value=reading.value,
        threshold=settings.stat_z_threshold,
        condition=direction,
        severity="warning",
        message=(
            f"{reading.sensor_type} reading {abs(stats.z_score):.1f}σ {direction} normal "
            f"({stats.mean:.2f} ± {stats.stddev:.2f})"
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
        alert_type="statistical_anomaly",
        z_score=stats.z_score,
        baseline_mean=stats.mean,
        baseline_stddev=stats.stddev,
    )
