import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.auth import verify_ws_token
from app.ws_manager import manager

log = logging.getLogger("ws_router")
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    try:
        verify_ws_token(token)
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(ws)
    try:
        while True:
            # Client doesn't need to send anything; just keep the connection
            # open and drop it if the browser tab closes.
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
