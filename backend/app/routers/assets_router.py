from fastapi import APIRouter, Depends, HTTPException

from app import alerts_db, assets_db, mqtt_client
from app.auth import get_current_user
from app.models import ASSET_STATUSES, AssetCreate, AssetUpdate

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
async def list_assets(_user: str = Depends(get_current_user)):
    return assets_db.list_assets()


@router.post("", status_code=201)
async def create_asset(payload: AssetCreate, _user: str = Depends(get_current_user)):
    if payload.status not in ASSET_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {ASSET_STATUSES}")
    if payload.asset_id and assets_db.get_asset(payload.asset_id, include_deleted=True):
        raise HTTPException(status_code=409, detail="asset_id already exists")
    return assets_db.create_asset(payload)


@router.get("/{asset_id}")
async def get_asset(asset_id: str, _user: str = Depends(get_current_user)):
    asset = assets_db.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{asset_id}")
async def update_asset(asset_id: str, payload: AssetUpdate, _user: str = Depends(get_current_user)):
    if payload.status is not None and payload.status not in ASSET_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {ASSET_STATUSES}")
    asset = assets_db.update_asset(asset_id, payload)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: str, _user: str = Depends(get_current_user)):
    ok = assets_db.soft_delete_asset(asset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Asset not found")


@router.get("/{asset_id}/detail")
async def asset_detail(asset_id: str, _user: str = Depends(get_current_user)):
    asset = assets_db.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    return {
        "asset": asset,
        "live_readings": mqtt_client.latest_readings_for(asset.linked_sensor_nodes),
        "alert_history": alerts_db.list_history(asset_id=asset_id, limit=50),
    }
