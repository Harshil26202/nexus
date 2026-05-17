"""WebSocket endpoint — real-time pipeline and agent event streaming."""
import asyncio
import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.redis_client import AGENT_CHANNEL, INCIDENT_CHANNEL, PIPELINE_CHANNEL, redis_pool

log = structlog.get_logger()
router = APIRouter()

_connections: dict[str, set[WebSocket]] = {
    "pipeline": set(),
    "agent": set(),
    "incident": set(),
}


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, room: str) -> None:
        await ws.accept()
        self._rooms.setdefault(room, set()).add(ws)
        log.info("ws.connected", room=room, total=len(self._rooms.get(room, [])))

    def disconnect(self, ws: WebSocket, room: str) -> None:
        self._rooms.get(room, set()).discard(ws)

    async def broadcast(self, room: str, data: str) -> None:
        dead: set[WebSocket] = set()
        for ws in list(self._rooms.get(room, [])):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._rooms.get(room, set()).discard(ws)


manager = ConnectionManager()


async def _redis_listener(channel_name: str, room: str) -> None:
    """Subscribe to a Redis pub/sub channel and broadcast to WebSocket room."""
    pubsub = await redis_pool.subscribe(channel_name)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await manager.broadcast(room, message["data"])
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel_name)


@router.websocket("/pipelines")
async def ws_pipelines(ws: WebSocket) -> None:
    await manager.connect(ws, "pipeline")
    listener = asyncio.create_task(_redis_listener(PIPELINE_CHANNEL, "pipeline"))
    try:
        while True:
            data = await ws.receive_text()
            # Support client-side ping
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(ws, "pipeline")
    finally:
        listener.cancel()


@router.websocket("/agents")
async def ws_agents(ws: WebSocket) -> None:
    await manager.connect(ws, "agent")
    listener = asyncio.create_task(_redis_listener(AGENT_CHANNEL, "agent"))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws, "agent")
    finally:
        listener.cancel()


@router.websocket("/incidents")
async def ws_incidents(ws: WebSocket) -> None:
    await manager.connect(ws, "incident")
    listener = asyncio.create_task(_redis_listener(INCIDENT_CHANNEL, "incident"))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws, "incident")
    finally:
        listener.cancel()
