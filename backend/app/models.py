from typing import Optional

from pydantic import BaseModel


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
    sensor_type: str
    value: float
    threshold: float
    condition: str
    severity: str
    message: str
    timestamp: str


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
