from fastapi import APIRouter, Depends

from app import mqtt_client
from app.auth import get_current_user

router = APIRouter(prefix="/api/control", tags=["control"])


@router.post("/anomaly/{node_id}")
async def trigger_anomaly(node_id: str, _user: str = Depends(get_current_user)):
    """Publishes a control message that the target sensor node subscribes to,
    causing it to inject a spike on its next tick. Lets the dashboard trigger
    an anomaly on demand for demo purposes."""
    mqtt_client.publish_control(f"anomaly/{node_id}", {"triggered_by": _user})
    return {"status": "triggered", "node_id": node_id}
