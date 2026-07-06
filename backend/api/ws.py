import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

from api.deps import is_valid_token

router = APIRouter()

connected_clients: List[WebSocket] = []
log_queue: asyncio.Queue = asyncio.Queue()


async def broadcast(message: str):
    for client in connected_clients[:]:
        try:
            await client.send_text(message)
        except Exception:
            connected_clients.remove(client)


@router.websocket("/ws/agents")
async def agent_stream(websocket: WebSocket):
    # Browsers can't set an Authorization header on WebSocket connections,
    # so the token travels as a query parameter (?token=...).
    token = websocket.query_params.get("token", "")
    if not token or not is_valid_token(token):
        await websocket.close(code=1008)  # policy violation
        return

    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
