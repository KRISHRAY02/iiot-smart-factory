from fastapi import APIRouter, Depends

from app import influx, mqtt_client
from app.auth import get_current_user
from app.models import StatusResponse
from app.ws_manager import manager

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("", response_model=StatusResponse)
async def status(_user: str = Depends(get_current_user)):
    return StatusResponse(
        mqtt_connected=mqtt_client.is_connected(),
        influx_connected=influx.is_connected(),
        connected_websocket_clients=manager.count,
        known_nodes=mqtt_client.known_nodes(),
    )
