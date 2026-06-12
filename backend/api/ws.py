import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

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
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
