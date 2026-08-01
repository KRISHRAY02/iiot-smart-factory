from typing import Optional

from fastapi import APIRouter, Depends, Query

from app import influx, mqtt_client
from app.auth import get_current_user

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
