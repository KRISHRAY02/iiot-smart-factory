import asyncio
import json
import logging

from fastapi import WebSocket

log = logging.getLogger("ws_manager")


class ConnectionManager:
    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)

    @property
    def count(self) -> int:
        return len(self._connections)

    async def _broadcast(self, message: dict):
        dead = []
        payload = json.dumps(message)
        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    def broadcast_threadsafe(self, message: dict):
        """Called from the MQTT client's background thread."""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)


manager = ConnectionManager()
