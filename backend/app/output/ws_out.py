import asyncio
import json
import time
import websockets
import logging
from app.storage.config_store import ConfigStore

logger = logging.getLogger(__name__)

class WsOutputDriver:
    def __init__(self, config_store: ConfigStore):
        self.config_store = config_store
        self.clients = set()
        self.server = None
        self.current_port = 0
        self.enabled = False
        self._check_task = None
        
    async def start(self):
        self._check_task = asyncio.create_task(self._watch_config())
        
    async def stop(self):
        if self._check_task:
            self._check_task.cancel()
        await self._stop_server()

    async def _stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        for ws in list(self.clients):
            await ws.close()
        self.clients.clear()

    async def _watch_config(self):
        while True:
            cfg = self.config_store.get_config().output.ws
            
            if cfg.enabled != self.enabled or cfg.port != self.current_port:
                await self._stop_server()
                self.enabled = cfg.enabled
                self.current_port = cfg.port
                
                if self.enabled:
                    try:
                        self.server = await websockets.serve(self._handler, "0.0.0.0", self.current_port)
                        logger.info(f"Output WS server started on port {self.current_port}")
                    except Exception as e:
                        logger.error(f"Failed to start Output WS on port {self.current_port}: {e}")
                        
            await asyncio.sleep(2.0)
                        
    async def _handler(self, websocket):
        self.clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)

    def _broadcast(self, msg_dict: dict):
        if not self.enabled or not self.clients:
            return
        msg = json.dumps(msg_dict)
        for ws in list(self.clients):
            asyncio.create_task(ws.send(msg))

    def send_blobs(self, blobs: list[dict]):
        self._broadcast({
            "v": 1,
            "type": "blobs",
            "ts": int(time.time() * 1000),
            "data": {"blobs": blobs}
        })
        
    def send_zone_event(self, event: str, zone_id: str, blob_id: int, x: float, y: float, count: int):
        self._broadcast({
            "v": 1,
            "type": "zoneEvent",
            "ts": int(time.time() * 1000),
            "data": {
                "event": event,
                "zoneId": zone_id,
                "blobId": blob_id,
                "x": x,
                "y": y,
                "count": count
            }
        })
