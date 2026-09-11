from typing import Literal

from fastapi import APIRouter, Depends

from app import mqtt_client
from app.auth import get_current_user

router = APIRouter(prefix="/api/control", tags=["control"])


@router.post("/anomaly/{node_id}")
async def trigger_anomaly(
    node_id: str,
    mode: Literal["spike", "drift"] = "spike",
    _user: str = Depends(get_current_user),
):
    """Publishes a control message that the target sensor node subscribes to.
    "spike" jumps past the static hard-limit threshold (the classic demo).
    "drift" nudges the value a few multiples of its own noise stddev,
    sustained over more ticks — enough to trip the statistical z-score
    detector while deliberately staying under the static threshold, showing
    off detection the old static check alone would miss."""
    mqtt_client.publish_control(f"anomaly/{node_id}", {"triggered_by": _user, "mode": mode})
    return {"status": "triggered", "node_id": node_id, "mode": mode}
