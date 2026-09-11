from typing import Optional

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    node_id: str
    sensor_type: str
    value: float
    unit: str
    anomaly: bool = False
    timestamp: str


class Alert(BaseModel):
    id: str
    node_id: str
    asset_id: Optional[str] = None
    sensor_type: str
    value: float
    threshold: float
    condition: str
    severity: str
    message: str
    timestamp: str
    alert_type: str = "threshold_breach"
    z_score: Optional[float] = None
    baseline_mean: Optional[float] = None
    baseline_stddev: Optional[float] = None


ASSET_STATUSES = ("Operational", "Under Maintenance", "Offline", "Decommissioned")


class AssetBase(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    asset_type: str
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    install_date: Optional[str] = None
    last_maintenance_date: Optional[str] = None
    next_scheduled_maintenance: Optional[str] = None
    status: str = "Operational"
    location: Optional[str] = None
    linked_sensor_nodes: list[str] = Field(default_factory=list)


class AssetCreate(AssetBase):
    asset_id: Optional[str] = None


class AssetUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: Optional[str] = None
    asset_type: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    install_date: Optional[str] = None
    last_maintenance_date: Optional[str] = None
    next_scheduled_maintenance: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    linked_sensor_nodes: Optional[list[str]] = None


class Asset(AssetBase):
    asset_id: str
    maintenance_overdue: bool = False
    created_at: str
    updated_at: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class StatusResponse(BaseModel):
    mqtt_connected: bool
    influx_connected: bool
    connected_websocket_clients: int
    known_nodes: list[str]
