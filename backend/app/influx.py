import logging
from datetime import datetime
from typing import Optional

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import settings
from app.models import SensorReading

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


def _node_ids_filter_clause(node_ids: Optional[list[str]]) -> str:
    if not node_ids:
        return ""
    if len(node_ids) == 1:
        return f'|> filter(fn: (r) => r["node_id"] == "{node_ids[0]}")'
    conditions = " or ".join(f'r["node_id"] == "{n}"' for n in node_ids)
    return f"|> filter(fn: (r) => {conditions})"


def count_range(start_rfc3339: str, end_rfc3339: str, node_ids: Optional[list[str]] = None) -> int:
    filter_clause = _node_ids_filter_clause(node_ids)
    flux = f'''
    from(bucket: "{settings.influx_bucket}")
      |> range(start: {start_rfc3339}, stop: {end_rfc3339})
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


def stream_range(start_rfc3339: str, end_rfc3339: str, node_ids: Optional[list[str]] = None):
    """Streams readings for CSV export via the InfluxDB client's native
    streaming query API, instead of materializing the whole result set."""
    filter_clause = _node_ids_filter_clause(node_ids)
    flux = f'''
    from(bucket: "{settings.influx_bucket}")
      |> range(start: {start_rfc3339}, stop: {end_rfc3339})
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
      {filter_clause}
      |> sort(columns: ["_time"])
    '''
    for record in _query_api.query_stream(flux):
        yield {
            "node_id": record.values.get("node_id"),
            "sensor_type": record.values.get("sensor_type"),
            "value": record.get_value(),
            "timestamp": record.get_time().isoformat(),
        }


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
