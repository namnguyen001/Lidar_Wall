import asyncio
from typing import Any
from app.storage.config_store import ConfigStore
from app.output.osc import OscOutputDriver
from app.output.tuio import TuioOutputDriver
from app.output.ws_out import WsOutputDriver

class OutputManager:
    def __init__(self, config_store: ConfigStore):
        self.config_store = config_store
        self.osc = OscOutputDriver(config_store)
        self.tuio = TuioOutputDriver(config_store)
        self.ws = WsOutputDriver(config_store)
        self.active_blobs: dict[int, dict] = {}
        self.task = None

    async def start(self):
        await self.ws.start()

    async def stop(self):
        await self.ws.stop()

    def process_blobs(self, blobs: list[Any], ts: float):
        cfg = self.config_store.get_config()
        coord_cfg = cfg.output.coordinate
        
        transformed = []
        for b in blobs:
            u = getattr(b, 'u', b.get('u') if isinstance(b, dict) else 0)
            v = getattr(b, 'v', b.get('v') if isinstance(b, dict) else 0)
            vx = getattr(b, 'vu', b.get('vu') if isinstance(b, dict) else 0)
            vy = getattr(b, 'vv', b.get('vv') if isinstance(b, dict) else 0)
            
            x, y = u, v
            if coord_cfg.flipY:
                y = 1.0 - y
                vy = -vy
                
            if coord_cfg.space == "px":
                x = x * coord_cfg.wallWidthPx
                y = y * coord_cfg.wallHeightPx
                vx = vx * coord_cfg.wallWidthPx
                vy = vy * coord_cfg.wallHeightPx
                
            size = getattr(b, 'size_mm', getattr(b, 'sizeMm', b.get('sizeMm') if isinstance(b, dict) else 0))
            b_id = getattr(b, 'id', b.get('id') if isinstance(b, dict) else 0)
            state = getattr(b, 'state', b.get('state') if isinstance(b, dict) else "active")
            
            tb = {
                "id": b_id, "x": x, "y": y, "sizeMm": size, "vx": vx, "vy": vy, "state": state,
                "u": u, "v": v
            }
            transformed.append(tb)

        current_ids = {b["id"] for b in transformed if b["state"] == "active"}
        for old_id in self.active_blobs.keys():
            if old_id not in current_ids:
                self.osc.send_up(old_id)
                self.tuio.send_up(old_id)
        
        self.active_blobs = {b["id"]: b for b in transformed if b["state"] == "active"}
        
        active_list = list(self.active_blobs.values())
        self.osc.send_blobs(active_list)
        self.tuio.send_blobs(active_list)
        self.ws.send_blobs(active_list)

    def process_zone_event(self, event: str, zone_id: str, blob_id: int, u: float, v: float, count: int):
        cfg = self.config_store.get_config()
        coord_cfg = cfg.output.coordinate
        
        x, y = u, v
        if coord_cfg.flipY:
            y = 1.0 - y
        if coord_cfg.space == "px":
            x = x * coord_cfg.wallWidthPx
            y = y * coord_cfg.wallHeightPx
            
        self.osc.send_zone_event(event, zone_id, blob_id, x, y, count)
        self.ws.send_zone_event(event, zone_id, blob_id, x, y, count)
