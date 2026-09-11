from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app import alerts_db
from app.auth import get_current_user
from app.models import ALERT_SEVERITIES, ALERT_STATUSES, ResolveAlertRequest

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_active_alerts(asset_id: Optional[str] = None, _user: str = Depends(get_current_user)):
    """Alerts still visible in the Active Alerts panel (active or acknowledged)."""
    return alerts_db.list_open(asset_id=asset_id)


@router.get("/history")
async def alert_history(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    asset_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    _user: str = Depends(get_current_user),
):
    if status is not None and status not in ALERT_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {ALERT_STATUSES}")
    if severity is not None and severity not in ALERT_SEVERITIES:
        raise HTTPException(status_code=422, detail=f"severity must be one of {ALERT_SEVERITIES}")
    return alerts_db.list_history(
        status=status, severity=severity, asset_id=asset_id, start=start, end=end, limit=limit
    )


@router.get("/summary")
async def alert_summary(_user: str = Depends(get_current_user)):
    return alerts_db.summary_stats()


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, _user: str = Depends(get_current_user)):
    record = alerts_db.acknowledge_alert(alert_id, _user)
    if record is None:
        existing = alerts_db.get_alert(alert_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        raise HTTPException(status_code=409, detail=f"Alert is already {existing.status}")
    return record


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    payload: ResolveAlertRequest = ResolveAlertRequest(),
    _user: str = Depends(get_current_user),
):
    record = alerts_db.resolve_alert(alert_id, _user, resolution_note=payload.resolution_note)
    if record is None:
        existing = alerts_db.get_alert(alert_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        raise HTTPException(status_code=409, detail=f"Alert is already {existing.status}")
    return record
