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


def write_reading(reading: SensorReading, rolling_mean: Optional[float] = None, rolling_stddev: Optional[float] = None):
    point = (
        Point("sensor_reading")
        .tag("node_id", reading.node_id)
        .tag("sensor_type", reading.sensor_type)
        .field("value", reading.value)
        .field("anomaly", reading.anomaly)
        .time(reading.timestamp, WritePrecision.NS)
    )
    if rolling_mean is not None:
        point = point.field("rolling_mean", rolling_mean)
    if rolling_stddev is not None:
        point = point.field("rolling_stddev", rolling_stddev)
    _write_api.write(bucket=settings.influx_bucket, record=point)


def write_alert(alert: Alert):
    point = (
        Point("alert")
        .tag("node_id", alert.node_id)
        .tag("asset_id", alert.asset_id or "")
        .tag("sensor_type", alert.sensor_type)
        .tag("severity", alert.severity)
        .tag("alert_type", alert.alert_type)
        .field("id", alert.id)
        .field("value", alert.value)
        .field("threshold", alert.threshold)
        .field("condition", alert.condition)
        .field("message", alert.message)
        .time(alert.timestamp, WritePrecision.NS)
    )
    if alert.z_score is not None:
        point = point.field("z_score", alert.z_score)
    if alert.baseline_mean is not None:
        point = point.field("baseline_mean", alert.baseline_mean)
    if alert.baseline_stddev is not None:
        point = point.field("baseline_stddev", alert.baseline_stddev)
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
      |> filter(fn: (r) => r["_field"] == "value" or r["_field"] == "rolling_mean" or r["_field"] == "rolling_stddev")
      {filter_clause}
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    '''
    tables = _query_api.query(flux)
    results = []
    for table in tables:
        for record in table.records:
            values = record.values
            results.append(
                {
                    "node_id": values.get("node_id"),
                    "sensor_type": values.get("sensor_type"),
                    "value": values.get("value"),
                    "rolling_mean": values.get("rolling_mean"),
                    "rolling_stddev": values.get("rolling_stddev"),
                    "timestamp": record.get_time().isoformat(),
                }
            )
    return results


def count_readings(node_id: Optional[str], hours: int) -> int:
    filter_clause = f'|> filter(fn: (r) => r["node_id"] == "{node_id}")' if node_id else ""
    flux = f'''
    from(bucket: "{settings.influx_bucket}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
      {filter_clause}
      |> count()
    '''
    tables = _query_api.query(flux)
    total = 0
    for table in tables:
        for record in table.records:
            total += record.get_value()
    return total


def query_recent_alerts(limit: int = 100, asset_id: Optional[str] = None):
    asset_filter = f'|> filter(fn: (r) => r["asset_id"] == "{asset_id}")' if asset_id else ""
    flux = f'''
    from(bucket: "{settings.influx_bucket}")
      |> range(start: -7d)
      |> filter(fn: (r) => r["_measurement"] == "alert")
      {asset_filter}
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
                    "asset_id": values.get("asset_id") or None,
                    "sensor_type": values.get("sensor_type"),
                    "severity": values.get("severity"),
                    "alert_type": values.get("alert_type") or "threshold_breach",
                    "value": values.get("value"),
                    "threshold": values.get("threshold"),
                    "condition": values.get("condition"),
                    "message": values.get("message"),
                    "z_score": values.get("z_score"),
                    "baseline_mean": values.get("baseline_mean"),
                    "baseline_stddev": values.get("baseline_stddev"),
                    "timestamp": record.get_time().isoformat(),
                }
            )
    return results
