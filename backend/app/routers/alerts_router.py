from fastapi import APIRouter, Depends, Query

from app import influx
from app.auth import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(limit: int = Query(100, ge=1, le=500), _user: str = Depends(get_current_user)):
    return influx.query_recent_alerts(limit)
