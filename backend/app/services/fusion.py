import asyncio
import logging
import time
import numpy as np

from app.core.tracking import Tracker
from app.storage.config_store import ConfigStore
from app.services.ws_hub import WsHub
from app.core.scan_area import filter_inside_quad

logger = logging.getLogger(__name__)

class FusionService:
    def __init__(self, config_store: ConfigStore, ws_hub: WsHub):
        self.config_store = config_store
        self.ws_hub = ws_hub
        self.tracker = Tracker()
        self._task = None
        self.latest_detections = {}
        self.zone_engine = None

    def push_detections(self, lidar_id: str, u: np.ndarray, v: np.ndarray, sizes: np.ndarray, ts: float):
        self.latest_detections[lidar_id] = {
            "u": u, "v": v, "sizes": sizes, "ts": ts
        }

    async def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._run_pipeline())
            
    async def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run_pipeline(self):
        while True:
            t_start = time.perf_counter()
            await asyncio.sleep(1.0 / 30.0) # Fixed 30Hz tick
            
            cfg = self.config_store.get_config()
            now = time.time()
            
            all_u = []
            all_v = []
            all_sizes = []
            all_sources = []
            
            # 1. Collect valid detections from all lidars
            for lidar_conf in cfg.lidars:
                if not lidar_conf.enabled:
                    continue
                
                det = self.latest_detections.get(lidar_conf.id)
                if not det:
                    continue
                    
                # Age <= 150ms
                if now - det["ts"] > 0.150:
                    continue
                    
                # Filter by coverageUv
                u = det["u"]
                v = det["v"]
                sizes = det["sizes"]
                if len(u) == 0:
                    continue
                    
                active_lidars = [l for l in cfg.lidars if l.enabled]
                if len(active_lidars) <= 1:
                    # Single lidar: accept all detections within screen area (with slight margin)
                    in_mask = (u >= -0.05) & (u <= 1.05) & (v >= -0.05) & (v <= 1.05)
                else:
                    quad = np.array(lidar_conf.coverageUv) if lidar_conf.coverageUv else np.array([[0,0],[1,0],[1,1],[0,1]])
                    in_mask = filter_inside_quad(u, v, quad)
                
                u_valid = np.clip(u[in_mask], 0.0, 1.0)
                v_valid = np.clip(v[in_mask], 0.0, 1.0)
                all_u.extend(u_valid)
                all_v.extend(v_valid)
                all_sizes.extend(sizes[in_mask])
                all_sources.extend([[lidar_conf.id]] * np.sum(in_mask))
            
            # 2. Merge detections
            fused_u = []
            fused_v = []
            fused_sizes = []
            
            if len(all_u) > 0:
                all_u = np.array(all_u)
                all_v = np.array(all_v)
                all_sizes = np.array(all_sizes)
                
                wall_w = cfg.wall.widthMm
                wall_h = cfg.wall.heightMm
                merge_r2 = cfg.blob.mergeRadiusMm ** 2
                
                used = np.zeros(len(all_u), dtype=bool)
                
                for i in range(len(all_u)):
                    if used[i]:
                        continue
                    
                    # Find all points within merge radius
                    dx = (all_u - all_u[i]) * wall_w
                    dy = (all_v - all_v[i]) * wall_h
                    dist2 = dx*dx + dy*dy
                    
                    # Also don't merge points already used
                    close_mask = (dist2 < merge_r2) & (~used)
                    
                    # Weighted average by size (or just mean)
                    group_u = all_u[close_mask]
                    group_v = all_v[close_mask]
                    group_s = all_sizes[close_mask]
                    
                    # For simplicity, just mean
                    fused_u.append(np.mean(group_u))
                    fused_v.append(np.mean(group_v))
                    fused_sizes.append(np.max(group_s)) # keep max size
                    
                    used[close_mask] = True
            
            # 3. Track
            tracked = self.tracker.update(
                np.array(fused_u), np.array(fused_v), np.array(fused_sizes), time.time()
            )
            
            blob_data = []
            for tb in tracked:
                if tb.state == "active":
                    blob_data.append({
                        "id": tb.id,
                        "u": round(float(tb.u), 4),
                        "v": round(float(tb.v), 4),
                        "sizeMm": round(float(tb.size_mm), 1),
                        "vu": round(float(tb.vu), 4),
                        "vv": round(float(tb.vv), 4),
                        "state": tb.state,
                        "ageFrames": tb.age_frames
                    })
                    
            if len(blob_data) > 0:
                asyncio.create_task(self.ws_hub.broadcast_events({
                    "v": 1, "type": "blobs", "ts": int(time.time()*1000),
                    "data": {"blobs": blob_data}
                }))
            
            # ALWAYS push to output manager (even when empty) so OSC/TUIO can clear up blobs and emit heartbeat!
            if getattr(self, 'output_manager', None):
                self.output_manager.process_blobs(blob_data, time.time())
            
            if self.zone_engine:
                active_blobs = [tb for tb in tracked if tb.state == "active"]
                asyncio.create_task(self.zone_engine.process_blobs(active_blobs, time.time()))
