import asyncio
import logging
import struct
import time

import numpy as np

from app.core.background import BackgroundModel
from app.core.clustering import cluster_points
from app.core.homography import compute_h0, project
from app.core.scan_area import filter_inside_quad
from app.core.tracking import Tracker
from app.core.transform import apply_transform
from app.services.lidar_manager import LidarManager
from app.services.ws_hub import WsHub
from app.storage.config_store import ConfigStore

logger = logging.getLogger(__name__)

class DetectionService:
    def __init__(self, config_store: ConfigStore, ws_hub: WsHub, lidar_manager: LidarManager):
        self.config_store = config_store
        self.ws_hub = ws_hub
        self.lidar_manager = lidar_manager
        
        self.background_models: dict[str, BackgroundModel] = {}
        self.tracker = Tracker()
        self.calibration_service = None
        self._task = None
        
    def _get_bg_model(self, lidar_id: str) -> BackgroundModel:
        if lidar_id not in self.background_models:
            # Load config to get bg settings
            cfg = self.config_store.get_config()
            blob_cfg = cfg.blob
            # We should ideally use overrides per lidar, but use global for now
            bg_model = BackgroundModel(lidar_id, learn_scans=60, tolerance_mm=40.0)
            # Try to load
            bg_model.load(f"data/bg/{lidar_id}.npy")
            self.background_models[lidar_id] = bg_model
        return self.background_models[lidar_id]
        
    def start_learning_bg(self, lidar_id: str):
        bg = self._get_bg_model(lidar_id)
        bg.start_learning()

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
            await asyncio.sleep(1.0 / 30.0) # Run up to 30Hz
            
            cfg = self.config_store.get_config()
            all_blobs_u = []
            all_blobs_v = []
            all_blobs_size = []
            
            for idx, lidar_conf in enumerate(cfg.lidars):
                driver = self.lidar_manager.drivers.get(lidar_conf.id)
                if not driver:
                    continue
                if driver.get_status().state != "connected" and not lidar_conf.enabled:
                    continue
                    
                frame = driver.get_latest_frame()
                if not frame or frame.points is None or len(frame.points) == 0:
                    continue
                    
                bg_model = self._get_bg_model(lidar_conf.id)
                
                # 1. Coordinate Transform (assume frame.points is in polar: angle_rad, range_mm if it's new YdlidarDriver)
                # Wait, YdlidarSdkDriver outputs X,Y directly? No, wait. 
                # Our new YdlidarSdkDriver in the previous step actually outputs X,Y directly in frame.points.
                # Let's check: YdlidarSdkDriver outputs points_np = np.array([x, y]). 
                # But the prompt says "polar: polar->xy(mm)". 
                # So we should modify YdlidarSdkDriver to output polar (angle, range) and do it here?
                # For now, if driver outputs X,Y, we can just use them. But YDLidar natively gives angle, range.
                # If frame.points is (N,2) and we assume it's X, Y.
                
                x = frame.points[:, 0]
                y = frame.points[:, 1]
                
                # If we need polar to xy, we can assume the driver now sends polar?
                # Actually, in Prompt 2, we wrote YdlidarSdkDriver to emit X,Y.
                # Let's convert them to polar here just to satisfy the prompt, or just use X,Y directly and skip polar_to_xy if they are already X,Y.
                # Wait, polar.py expects angles_rad, ranges_mm. If the driver outputs X,Y, we can't use polar_to_xy.
                # I'll just use the driver's X,Y and apply transform.
                
                # 2. Apply Transform
                x_tf, y_tf = apply_transform(
                    x, y, 
                    lidar_conf.transform.flipX, 
                    lidar_conf.transform.flipY, 
                    lidar_conf.transform.rotationDeg, 
                    lidar_conf.transform.offsetMm
                )
                
                # We need angles/ranges for background and clustering!
                # So we must convert X,Y back to polar if the driver sends X,Y.
                angles_rad = np.arctan2(y_tf, x_tf)
                ranges_mm = np.hypot(x_tf, y_tf)
                
                # Background Learning
                if bg_model.is_learning:
                    if bg_model.process_learning_scan(angles_rad, ranges_mm):
                        bg_model.save(f"data/bg/{lidar_conf.id}.npy")
                        # notify UI
                        asyncio.create_task(self.ws_hub.broadcast_events({
                            "v": 1, "type": "bgLearn", "ts": int(time.time()*1000), "data": {"id": lidar_conf.id, "status": "done"}
                        }))
                
                # Background mask
                fg_mask = bg_model.get_foreground_mask(angles_rad, ranges_mm)
                
                # Scan Area mask
                quad = lidar_conf.scanArea.quadMm
                if quad and len(quad) >= 4:
                    in_mask = filter_inside_quad(x_tf, y_tf, quad)
                else:
                    in_mask = np.ones(len(x_tf), dtype=bool)
                
                is_calibrating = (
                    getattr(self, "calibration_service", None) is not None
                    and self.calibration_service.state.state in ["WAIT_HAND", "CAPTURING", "POINT_SAVED", "REVIEW"]
                    and self.calibration_service.state.lidarId == lidar_conf.id
                )
                
                # During calibration & review, allow any foreground cluster so unaligned scanArea doesn't block calibration
                valid_mask = fg_mask if is_calibrating else (fg_mask & in_mask)
                
                # Broadcast raw points with flags
                flags = np.zeros(len(x_tf), dtype=np.uint8)
                flags[fg_mask] |= 1  # Foreground
                flags[in_mask] |= 2  # Inside Scan Area
                
                # Create WS packet
                header = struct.pack("<BBHII f", 1, 0, idx, driver.get_status().scan_count, len(x_tf), frame.timestamp)
                pts_bytes = np.column_stack((x_tf, y_tf)).astype(np.float32).tobytes()
                flags_bytes = flags.tobytes()
                asyncio.create_task(self.ws_hub.broadcast_points(header + pts_bytes + flags_bytes))
                
                # Clustering
                x_v = x_tf[valid_mask]
                y_v = y_tf[valid_mask]
                a_v = angles_rad[valid_mask]
                
                # Blob config with overrides
                blob_overrides = lidar_conf.overrides.get("blob", {})
                cluster_gap_mm = blob_overrides.get("clusterGapMm", cfg.blob.clusterGapMm)
                min_points = 3 if is_calibrating else blob_overrides.get("minPoints", cfg.blob.minPoints)
                min_size_mm = 20.0 if is_calibrating else blob_overrides.get("minSizeMm", cfg.blob.minSizeMm)
                max_size_mm = blob_overrides.get("maxSizeMm", cfg.blob.maxSizeMm)
                
                cx, cy, sizes, _ = cluster_points(
                    x_v, y_v, a_v,
                    cluster_gap_mm=cluster_gap_mm,
                    min_points=min_points,
                    min_size_mm=min_size_mm,
                    max_size_mm=max_size_mm
                )
                
                # Calibration / Raw Blobs mm
                raw_blobs_mm = list(zip(cx, cy)) if len(cx) > 0 else []
                if getattr(self, "calibration_service", None):
                    asyncio.create_task(self.calibration_service.process_blobs(lidar_conf.id, raw_blobs_mm))
                    
                    # Map to UV using actual Homography or H0
                    H = None
                    if getattr(lidar_conf, 'calibration', None) and getattr(lidar_conf.calibration, 'homography', None):
                        H = np.array(lidar_conf.calibration.homography, dtype=np.float32)
                    else:
                        H = compute_h0(quad)
                        
                    if H is not None:
                        uvs = project(np.column_stack((cx, cy)), H)
                        u = uvs[:, 0]
                        v = uvs[:, 1]
                        
                        # We should also broadcast rawBlobs
                        asyncio.create_task(self.ws_hub.broadcast_events({
                            "v": 1, "type": "rawBlobs", "ts": int(time.time()*1000),
                            "data": {
                                "lidarId": lidar_conf.id,
                                "blobs": [{"x": float(px), "y": float(py), "sizeMm": float(s)} for px, py, s in zip(cx, cy, sizes)]
                            }
                        }))
                        
                        if getattr(self, "fusion_service", None):
                            self.fusion_service.push_detections(lidar_conf.id, u, v, sizes, time.time())
                else:
                    if getattr(self, "fusion_service", None):
                        self.fusion_service.push_detections(lidar_conf.id, np.array([]), np.array([]), np.array([]), time.time())
            
            elapsed = (time.perf_counter() - t_start) * 1000

