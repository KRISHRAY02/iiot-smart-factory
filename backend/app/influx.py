import logging
from datetime import datetime
from typing import Optional

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import settings
from app.models import Alert, SensorReading

log = logging.getLogger("influx")

_client: Optional[InfluxDBClient] = None
_write_api = None
_query_api = None


def connect():
    global _client, _write_api, _query_api
    _client = InfluxDBClient(url=settings.influx_url, token=settings.influx_token, org=settings.influx_org)
    _write_api = _client.write_api(write_options=SYNCHRONOUS)
    _query_api = _client.query_api()


def is_connected() -> bool:
    if _client is None:
        return False
    try:
        return _client.ping()
    except Exception:
        return False


def write_reading(reading: SensorReading):
    point = (
        Point("sensor_reading")
        .tag("node_id", reading.node_id)
        .tag("sensor_type", reading.sensor_type)
        .field("value", reading.value)
        .field("anomaly", reading.anomaly)
        .time(reading.timestamp, WritePrecision.NS)
    )
    _write_api.write(bucket=settings.influx_bucket, record=point)


def write_alert(alert: Alert):
    point = (
        Point("alert")
        .tag("node_id", alert.node_id)
        .tag("sensor_type", alert.sensor_type)
        .tag("severity", alert.severity)
        .field("id", alert.id)
        .field("value", alert.value)
        .field("threshold", alert.threshold)
        .field("condition", alert.condition)
        .field("message", alert.message)
        .time(alert.timestamp, WritePrecision.NS)
    )
    _write_api.write(bucket=settings.influx_bucket, record=point)


def query_history(node_id: Optional[str], sensor_type: Optional[str], hours: int):
    filters = []
    if node_id:
        filters.append(f'r["node_id"] == "{node_id}"')
    if sensor_type:
        filters.append(f'r["sensor_type"] == "{sensor_type}"')
    filter_clause = f"|> filter(fn: (r) => {' and '.join(filters)})" if filters else ""

    flux = f'''
    from(bucket: "{settings.influx_bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
      {filter_clause}
      |> sort(columns: ["_time"])
    '''
    tables = _query_api.query(flux)
    results = []
    for table in tables:
        for record in table.records:
            results.append(
                {
                    "node_id": record.values.get("node_id"),
                    "sensor_type": record.values.get("sensor_type"),
                    "value": record.get_value(),
                    "timestamp": record.get_time().isoformat(),
                }
            )
    return results


def query_recent_alerts(limit: int = 100):
    flux = f'''
    from(bucket: "{settings.influx_bucket}")
      |> range(start: -7d)
      |> filter(fn: (r) => r["_measurement"] == "alert")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit})
    '''
    tables = _query_api.query(flux)
    results = []
    for table in tables:
        for record in table.records:
            values = record.values
            results.append(
                {
                    "id": values.get("id"),
                    "node_id": values.get("node_id"),
                    "sensor_type": values.get("sensor_type"),
                    "severity": values.get("severity"),
                    "value": values.get("value"),
                    "threshold": values.get("threshold"),
                    "condition": values.get("condition"),
                    "message": values.get("message"),
                    "timestamp": record.get_time().isoformat(),
                }
            )
    return results
