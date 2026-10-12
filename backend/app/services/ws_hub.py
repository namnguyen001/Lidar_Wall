import asyncio
import json
import orjson

from fastapi import WebSocket, WebSocketDisconnect


class WsHub:
    def __init__(self):
        self.events_clients: list[WebSocket] = []
        self.points_clients: list[WebSocket] = []

    async def connect_events(self, websocket: WebSocket):
        await websocket.accept()
        self.events_clients.append(websocket)
        # Send hello
        hello_msg = {
            "v": 1,
            "type": "hello",
            "ts": int(asyncio.get_event_loop().time() * 1000),
            "data": {"serverVersion": "1.0.0", "config": {}}
        }
        await websocket.send_text(json.dumps(hello_msg))
        try:
            while True:
                _ = await websocket.receive_text()
                # handle subscribe etc later
        except WebSocketDisconnect:
            if websocket in self.events_clients:
                self.events_clients.remove(websocket)

    async def connect_points(self, websocket: WebSocket):
        await websocket.accept()
        self.points_clients.append(websocket)
        try:
            while True:
                _ = await websocket.receive_text()
        except WebSocketDisconnect:
            if websocket in self.points_clients:
                self.points_clients.remove(websocket)

    async def broadcast_events(self, message: dict):
        if not self.events_clients: return
        msg_str = orjson.dumps(message, option=orjson.OPT_SERIALIZE_NUMPY).decode('utf-8')
        for client in self.events_clients:
            try:
                await client.send_text(msg_str)
            except (RuntimeError, WebSocketDisconnect):
                if client in self.events_clients:
                    self.events_clients.remove(client)

    async def broadcast_points(self, message: bytes):
        if not self.points_clients: return
        for client in self.points_clients:
            try:
                await client.send_bytes(message)
            except (RuntimeError, WebSocketDisconnect):
                if client in self.points_clients:
                    self.points_clients.remove(client)
