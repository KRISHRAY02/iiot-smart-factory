from fastapi import APIRouter, Depends

from app import node_health
from app.auth import get_current_user
from app.models import NodeHealthStatus

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


@router.get("/health", response_model=list[NodeHealthStatus])
async def node_health_status(_user: str = Depends(get_current_user)):
    return node_health.snapshot()
