#!/usr/bin/env bash
# Creates the mosquitto password file using the mosquitto_passwd tool that
# ships inside the eclipse-mosquitto image (avoids needing it installed
# locally). Run from the broker/ directory: ./generate-password-file.sh
#
# Reads MQTT_SENSOR_USERNAME/PASSWORD and MQTT_BACKEND_USERNAME/PASSWORD
# from ../backend/.env and ../sensor-nodes/.env if present, else prompts
# for values / falls back to defaults.

set -euo pipefail
cd "$(dirname "$0")"

SENSOR_USER="${MQTT_SENSOR_USERNAME:-sensor}"
SENSOR_PASS="${MQTT_SENSOR_PASSWORD:-change-me-sensor-pass}"
BACKEND_USER="${MQTT_BACKEND_USERNAME:-backend}"
BACKEND_PASS="${MQTT_BACKEND_PASSWORD:-change-me-backend-pass}"

mkdir -p config
rm -f config/passwd

docker run --rm -v "$(pwd)/config:/mosquitto/config" eclipse-mosquitto:2 \
  mosquitto_passwd -b -c /mosquitto/config/passwd "$SENSOR_USER" "$SENSOR_PASS"

docker run --rm -v "$(pwd)/config:/mosquitto/config" eclipse-mosquitto:2 \
  mosquitto_passwd -b /mosquitto/config/passwd "$BACKEND_USER" "$BACKEND_PASS"

echo "Wrote broker/config/passwd for users: $SENSOR_USER, $BACKEND_USER"
