from typing import Optional

from fastapi import APIRouter, Depends, Query

from app import baseline, influx, mqtt_client
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/readings", tags=["readings"])


@router.get("/history")
async def history(
    node_id: Optional[str] = None,
    sensor_type: Optional[str] = None,
    hours: int = Query(1, ge=1, le=168),
    _user: str = Depends(get_current_user),
):
    return influx.query_history(node_id, sensor_type, hours)


@router.get("/nodes")
async def nodes(_user: str = Depends(get_current_user)):
    return {"nodes": mqtt_client.known_nodes()}


@router.get("/debug/count")
async def debug_count(
    node_id: Optional[str] = None,
    hours: int = Query(1, ge=1, le=168),
    _user: str = Depends(get_current_user),
):
    return {"node_id": node_id, "hours": hours, "row_count": influx.count_readings(node_id, hours)}


@router.get("/debug/baseline/{node_id}")
async def debug_baseline(node_id: str, _user: str = Depends(get_current_user)):
    b = baseline.current_baseline(node_id)
    return {
        "node_id": node_id,
        "mean": b.mean,
        "stddev": b.stddev,
        "count": b.count,
        "min_points_required": settings.baseline_min_points,
        "window_size": settings.baseline_window_size,
        "z_threshold": settings.stat_z_threshold,
        "ready": b.mean is not None,
    }
