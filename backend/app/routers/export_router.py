from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app import alerts_db, assets_db, influx, node_health
from app.auth import get_current_user
from app.export_csv import csv_row
from app.models import ALERT_SEVERITIES, ALERT_STATUSES

router = APIRouter(prefix="/api/export", tags=["export"])

MAX_RANGE_DAYS = 7
MAX_EXPORT_ROWS = 50_000


def parse_range(start: str, end: str) -> tuple[datetime, datetime]:
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="start and end must be ISO 8601 timestamps")
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end must be after start")
    if end_dt - start_dt > timedelta(days=MAX_RANGE_DAYS):
        raise HTTPException(status_code=400, detail=f"Export range cannot exceed {MAX_RANGE_DAYS} days")
    return start_dt, end_dt


def _flux_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _export_filename(prefix: str, start_dt: datetime, end_dt: datetime) -> str:
    return f"{prefix}_{start_dt.date()}_to_{end_dt.date()}.csv"


def _too_many_rows_error(count: int) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=(
            f"This range has {count} rows, which exceeds the {MAX_EXPORT_ROWS}-row export "
            "cap — narrow the time range or filters."
        ),
    )


@router.get("/readings.csv")
async def export_readings_csv(
    start: str = Query(..., description="ISO 8601 UTC"),
    end: str = Query(..., description="ISO 8601 UTC"),
    node_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    _user: str = Depends(get_current_user),
):
    start_dt, end_dt = parse_range(start, end)

    node_ids: Optional[list[str]] = None
    if asset_id:
        asset = assets_db.get_asset(asset_id)
        if asset is None:
            raise HTTPException(status_code=400, detail="Unknown asset_id")
        node_ids = asset.linked_sensor_nodes
    elif node_id:
        node_ids = [node_id]

    flux_start, flux_end = _flux_ts(start_dt), _flux_ts(end_dt)

    count = influx.count_range(flux_start, flux_end, node_ids)
    if count > MAX_EXPORT_ROWS:
        raise _too_many_rows_error(count)
    if count == 0:
        raise HTTPException(status_code=400, detail="No readings found for this range and filters")

    def generate():
        yield csv_row(["timestamp_utc", "node_id", "asset_name", "sensor_type", "value", "unit"])
        for row in influx.stream_range(flux_start, flux_end, node_ids):
            asset = assets_db.find_asset_for_node(row["node_id"])
            yield csv_row(
                [
                    row["timestamp"],
                    row["node_id"],
                    asset.name if asset else "",
                    row["sensor_type"],
                    row["value"],
                    node_health.node_unit(row["node_id"]),
                ]
            )

    filename = _export_filename("readings", start_dt, end_dt)
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/alerts.csv")
async def export_alerts_csv(
    start: str = Query(..., description="ISO 8601 UTC"),
    end: str = Query(..., description="ISO 8601 UTC"),
    severity: Optional[str] = None,
    status: Optional[str] = None,
    asset_id: Optional[str] = None,
    _user: str = Depends(get_current_user),
):
    start_dt, end_dt = parse_range(start, end)
    if status is not None and status not in ALERT_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {ALERT_STATUSES}")
    if severity is not None and severity not in ALERT_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"severity must be one of {ALERT_SEVERITIES}")

    filter_kwargs = dict(
        status=status, severity=severity, asset_id=asset_id, start=start_dt.isoformat(), end=end_dt.isoformat()
    )

    count = alerts_db.count_history(**filter_kwargs)
    if count > MAX_EXPORT_ROWS:
        raise _too_many_rows_error(count)
    if count == 0:
        raise HTTPException(status_code=400, detail="No alerts found for this range and filters")

    columns = [
        "created_at",
        "asset_name",
        "node_id",
        "sensor_type",
        "alert_type",
        "severity",
        "status",
        "value",
        "z_score",
        "baseline_mean",
        "baseline_stddev",
        "acknowledged_by",
        "acknowledged_at",
        "resolved_by",
        "resolved_at",
        "resolution_note",
    ]

    def generate():
        yield csv_row(columns)
        for record in alerts_db.stream_history(**filter_kwargs):
            asset = assets_db.get_asset(record.asset_id) if record.asset_id else None
            yield csv_row(
                [
                    record.created_at,
                    asset.name if asset else "",
                    record.node_id,
                    record.sensor_type,
                    record.alert_type,
                    record.severity,
                    record.status,
                    record.value,
                    record.z_score,
                    record.baseline_mean,
                    record.baseline_stddev,
                    record.acknowledged_by,
                    record.acknowledged_at,
                    record.resolved_by,
                    record.resolved_at,
                    record.resolution_note,
                ]
            )

    filename = _export_filename("alerts", start_dt, end_dt)
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
