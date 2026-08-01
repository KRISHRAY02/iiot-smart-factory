"""
Virtual sensor node simulator.

Each container instance runs this script with NODE_ID env var set to one of
the node ids defined in config.yaml. It publishes a noisy/drifting signal for
that sensor over MQTT (TLS + username/password auth), and can inject a
sudden-spike anomaly either randomly (ANOMALY_PROBABILITY) or on demand via
a control topic (factory/control/anomaly/<node_id>) for demo purposes.
"""

import json
import logging
import os
import random
import ssl
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sensor-node")

CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config.yaml")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def find_node(config, node_id):
    for node in config["nodes"]:
        if node["id"] == node_id:
            return node
    raise ValueError(f"Node id '{node_id}' not found in {CONFIG_PATH}")


class SensorSimulator:
    def __init__(self, config, node_cfg):
        self.config = config
        self.node_cfg = node_cfg
        self.value = node_cfg["baseline"]
        self.drift_direction = random.choice([-1, 1])
        self.anomaly_active = False
        self.anomaly_ticks_remaining = 0
        self.anomaly_probability = float(os.environ.get("ANOMALY_PROBABILITY", "0.0"))

    def _drift(self):
        # Slow random-walk drift, occasionally reversing direction.
        if random.random() < 0.05:
            self.drift_direction *= -1
        self.value += self.drift_direction * self.node_cfg["drift_per_tick"]

    def _clamp(self, value):
        return max(self.node_cfg["min_value"], min(self.node_cfg["max_value"], value))

    def trigger_anomaly(self, duration_ticks=3):
        log.warning("Anomaly triggered on %s for %d tick(s)", self.node_cfg["id"], duration_ticks)
        self.anomaly_active = True
        self.anomaly_ticks_remaining = duration_ticks

    def next_reading(self):
        self._drift()
        noise = random.gauss(0, self.node_cfg["noise_stddev"])
        reading = self.value + noise

        if self.anomaly_probability > 0 and not self.anomaly_active:
            if random.random() < self.anomaly_probability:
                self.trigger_anomaly()

        if self.anomaly_active:
            spike_magnitude = (self.node_cfg["max_value"] - self.node_cfg["baseline"]) * 0.8
            reading += spike_magnitude
            self.anomaly_ticks_remaining -= 1
            if self.anomaly_ticks_remaining <= 0:
                self.anomaly_active = False

        return round(self._clamp(reading), 3)

    def payload(self):
        return {
            "node_id": self.node_cfg["id"],
            "sensor_type": self.node_cfg["type"],
            "value": self.next_reading(),
            "unit": self.node_cfg["unit"],
            "anomaly": self.anomaly_active,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def build_mqtt_client(config, node_id, simulator):
    broker_cfg = config["broker"]
    username = os.environ.get(broker_cfg["username_env"])
    password = os.environ.get(broker_cfg["password_env"])

    client = mqtt.Client(client_id=f"sensor-{node_id}", clean_session=True)
    if username:
        client.username_pw_set(username, password)

    if broker_cfg.get("use_tls"):
        client.tls_set(
            ca_certs=broker_cfg.get("ca_cert"),
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        # Self-signed cert for local dev is issued for the "mosquitto" hostname,
        # which matches the docker-compose service name used as broker.host.
        client.tls_insecure_set(False)

    control_topic = f"factory/control/anomaly/{node_id}"

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            log.info("Connected to broker as %s", node_id)
            client.subscribe(control_topic)
        else:
            log.error("Connection failed with code %s", rc)

    def on_message(client, userdata, msg):
        log.info("Manual anomaly trigger received on %s", msg.topic)
        simulator.trigger_anomaly()

    client.on_connect = on_connect
    client.on_message = on_message
    return client


def main():
    config = load_config()
    node_id = os.environ.get("NODE_ID")
    if not node_id:
        log.error("NODE_ID environment variable is required")
        sys.exit(1)

    node_cfg = find_node(config, node_id)
    simulator = SensorSimulator(config, node_cfg)
    client = build_mqtt_client(config, node_id, simulator)

    broker_cfg = config["broker"]
    interval = int(os.environ.get("PUBLISH_INTERVAL_SECONDS", config["publish_interval_seconds"]))

    retries = 0
    while True:
        try:
            client.connect(broker_cfg["host"], broker_cfg["port"], keepalive=30)
            break
        except Exception as exc:
            retries += 1
            wait = min(30, 2 ** retries)
            log.warning("Broker connect failed (%s), retrying in %ss", exc, wait)
            time.sleep(wait)

    client.loop_start()

    topic = node_cfg["topic"]
    try:
        while True:
            reading = simulator.payload()
            client.publish(topic, json.dumps(reading), qos=1)
            log.info("Published to %s: %s", topic, reading)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
