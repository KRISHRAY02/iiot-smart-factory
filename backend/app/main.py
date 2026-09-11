import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import alerts_db, assets_db, influx, mqtt_client
from app.config import settings
from app.routers import (
    alerts_router,
    assets_router,
    auth_router,
    control_router,
    readings_router,
    status_router,
    ws_router,
)
from app.ws_manager import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager.bind_loop(asyncio.get_running_loop())
    assets_db.connect()
    alerts_db.connect()
    influx.connect()
    mqtt_client.start()
    yield
    mqtt_client.stop()


app = FastAPI(title="IIoT Smart Factory Monitoring API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(assets_router.router)
app.include_router(readings_router.router)
app.include_router(alerts_router.router)
app.include_router(status_router.router)
app.include_router(control_router.router)
app.include_router(ws_router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
