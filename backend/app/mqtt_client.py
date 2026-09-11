import json
import logging
import ssl
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from app import assets_db, baseline, influx, rules
from app.config import settings
from app.models import SensorReading
from app.ws_manager import manager

log = logging.getLogger("mqtt_client")

_client: mqtt.Client | None = None
_connected = False
_known_nodes: set[str] = set()
_latest_readings: dict[str, dict] = {}


def is_connected() -> bool:
    return _connected


def known_nodes() -> list[str]:
    return sorted(_known_nodes)


def latest_reading(node_id: str) -> dict | None:
    return _latest_readings.get(node_id)


def latest_readings_for(node_ids: list[str]) -> list[dict]:
    return [_latest_readings[n] for n in node_ids if n in _latest_readings]


def _validate_and_stamp(raw_payload: bytes) -> SensorReading | None:
    try:
        data = json.loads(raw_payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        log.warning("Dropping malformed payload: %s", exc)
        return None

    try:
        reading = SensorReading(**data)
    except ValidationError as exc:
        log.warning("Dropping invalid reading: %s", exc)
        return None

    # Re-stamp with ingestion time if the device clock looks unreasonable;
    # otherwise trust the device timestamp for historical accuracy.
    try:
        datetime.fromisoformat(reading.timestamp)
    except ValueError:
        reading.timestamp = datetime.now(timezone.utc).isoformat()

    return reading


def _on_connect(client, userdata, flags, rc):
    global _connected
    if rc == 0:
        _connected = True
        log.info("Backend connected to MQTT broker")
        client.subscribe(settings.mqtt_topics, qos=1)
    else:
        _connected = False
        log.error("Backend MQTT connection failed with code %s", rc)


def _on_disconnect(client, userdata, rc):
    global _connected
    _connected = False
    log.warning("Backend disconnected from MQTT broker (rc=%s)", rc)


def _on_message(client, userdata, msg):
    reading = _validate_and_stamp(msg.payload)
    if reading is None:
        return

    _known_nodes.add(reading.node_id)

    stats = baseline.record_and_score(reading.node_id, reading.value)
    if stats.z_score is not None:
        log.info(
            "baseline %s: value=%.3f mean=%.3f stddev=%.3f z=%.2f (n=%d)",
            reading.node_id,
            reading.value,
            stats.mean,
            stats.stddev,
            stats.z_score,
            stats.count,
        )

    reading_payload = {**reading.model_dump(), "rolling_mean": stats.mean, "rolling_stddev": stats.stddev}
    _latest_readings[reading.node_id] = reading_payload

    try:
        influx.write_reading(reading, rolling_mean=stats.mean, rolling_stddev=stats.stddev)
    except Exception as exc:
        log.error("Failed to write reading to InfluxDB: %s", exc)

    manager.broadcast_threadsafe({"type": "reading", "data": reading_payload})

    asset = assets_db.find_asset_for_node(reading.node_id)
    if asset is not None and asset.status == "Under Maintenance":
        return

    fired_alerts = [
        rules.evaluate(reading),
        rules.evaluate_statistical(reading, stats),
    ]
    for alert in fired_alerts:
        if alert is None:
            continue
        alert.asset_id = asset.asset_id if asset is not None else None
        log.warning("ALERT [%s]: %s", alert.alert_type, alert.message)
        try:
            influx.write_alert(alert)
        except Exception as exc:
            log.error("Failed to write alert to InfluxDB: %s", exc)
        manager.broadcast_threadsafe({"type": "alert", "data": alert.model_dump()})


def start():
    global _client
    _client = mqtt.Client(client_id="backend-ingest", clean_session=True)
    _client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    if settings.mqtt_use_tls:
        _client.tls_set(
            ca_certs=settings.mqtt_ca_cert,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )

    _client.on_connect = _on_connect
    _client.on_disconnect = _on_disconnect
    _client.on_message = _on_message

    _client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    _client.loop_start()


def stop():
    if _client is not None:
        _client.loop_stop()
        _client.disconnect()


def publish_control(topic_suffix: str, payload: dict):
    if _client is not None:
        _client.publish(f"factory/control/{topic_suffix}", json.dumps(payload), qos=1)
