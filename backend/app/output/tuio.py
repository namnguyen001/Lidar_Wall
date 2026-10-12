import time
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.osc_bundle_builder import OscBundleBuilder
from pythonosc.osc_message_builder import OscMessageBuilder
from app.storage.config_store import ConfigStore

class TuioOutputDriver:
    def __init__(self, config_store: ConfigStore):
        self.config_store = config_store
        self.client = None
        self.current_host = ""
        self.current_port = 0
        self.last_send_time = 0.0
        self.fseq = 0

    def _ensure_client(self, host: str, port: int):
        if self.client is None or self.current_host != host or self.current_port != port:
            self.client = SimpleUDPClient(host, port)
            self.current_host = host
            self.current_port = port

    def send_blobs(self, blobs: list[dict]):
        cfg = self.config_store.get_config().output.tuio
        if not cfg.enabled:
            return
            
        now = time.perf_counter()
        if cfg.rateHz > 0:
            if now - self.last_send_time < (1.0 / cfg.rateHz):
                return
        self.last_send_time = now
        
        self._ensure_client(cfg.host, cfg.port)
        
        bundle = OscBundleBuilder(time.time())
        
        msg = OscMessageBuilder(address="/tuio/2Dcur")
        msg.add_arg("source")
        msg.add_arg("lidar-wall@localhost")
        bundle.add_content(msg.build())
        
        msg = OscMessageBuilder(address="/tuio/2Dcur")
        msg.add_arg("alive")
        for b in blobs:
            msg.add_arg(int(b["id"]))
        bundle.add_content(msg.build())
        
        coord_cfg = self.config_store.get_config().output.coordinate
        
        for b in blobs:
            msg = OscMessageBuilder(address="/tuio/2Dcur")
            msg.add_arg("set")
            msg.add_arg(int(b["id"]))
            
            u = float(b["u"])
            v = float(b["v"])
            
            # Extract velocities if available, otherwise 0
            vu = float(b.get("vu", 0.0))
            vv = float(b.get("vv", 0.0))
            
            if coord_cfg.flipY:
                v = 1.0 - v
                vv = -vv
                
            msg.add_arg(u)
            msg.add_arg(v)
            msg.add_arg(vu)
            msg.add_arg(vv)
            msg.add_arg(0.0) # m (motion acceleration)
            bundle.add_content(msg.build())
            
        msg = OscMessageBuilder(address="/tuio/2Dcur")
        msg.add_arg("fseq")
        msg.add_arg(self.fseq)
        bundle.add_content(msg.build())
        
        self.fseq += 1
        
        self.client.send(bundle.build())
        
    def send_up(self, blob_id: int):
        pass
