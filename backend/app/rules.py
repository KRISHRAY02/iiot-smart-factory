import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import yaml

from app.config import settings
from app.models import Alert, SensorReading

log = logging.getLogger("rules")

_ALERT_COOLDOWN_SECONDS = 30
_last_fired: dict[tuple, float] = {}


def load_rules():
    with open(settings.rules_config_path, "r") as f:
        return yaml.safe_load(f)["rules"]


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
    )
