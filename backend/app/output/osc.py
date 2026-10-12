import time
from pythonosc.udp_client import SimpleUDPClient
from app.storage.config_store import ConfigStore

class OscOutputDriver:
    def __init__(self, config_store: ConfigStore):
        self.config_store = config_store
        self.client = None
        self.current_host = ""
        self.current_port = 0
        self.last_send_time = 0.0

    def _ensure_client(self, host: str, port: int):
        if self.client is None or self.current_host != host or self.current_port != port:
            self.client = SimpleUDPClient(host, port)
            self.current_host = host
            self.current_port = port

    def send_blobs(self, blobs: list[dict]):
        cfg = self.config_store.get_config().output.osc
        if not cfg.enabled:
            return
            
        now = time.perf_counter()
        if cfg.rateHz > 0:
            if now - self.last_send_time < (1.0 / cfg.rateHz):
                return
        self.last_send_time = now
        
        self._ensure_client(cfg.host, cfg.port)
        
        self.client.send_message("/wall/count", len(blobs))
        
        for b in blobs:
            self.client.send_message("/wall/blob", [
                int(b["id"]),
                float(b["x"]),
                float(b["y"]),
                float(b["sizeMm"]),
                float(b["vx"]),
                float(b["vy"])
            ])
            
    def send_up(self, blob_id: int):
        cfg = self.config_store.get_config().output.osc
        if not cfg.enabled:
            return
        self._ensure_client(cfg.host, cfg.port)
        self.client.send_message("/wall/blob/up", int(blob_id))
        
    def send_zone_event(self, event: str, zone_id: str, blob_id: int, x: float, y: float, count: int):
        cfg = self.config_store.get_config().output.osc
        if not cfg.enabled:
            return
        self._ensure_client(cfg.host, cfg.port)
        
        if event in ("enter", "hold", "exit"):
            self.client.send_message(f"/wall/zone/{zone_id}/{event}", [
                int(blob_id),
                float(x),
                float(y)
            ])
        elif event == "count":
            self.client.send_message(f"/wall/zone/{zone_id}/count", int(count))
