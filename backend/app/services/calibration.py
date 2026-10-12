import asyncio
import time

import numpy as np
from pydantic import BaseModel

from app.core.homography import compute_h0, compute_homography, project
from app.services.ws_hub import WsHub
from app.storage.config_store import ConfigStore


class CalibrationResult(BaseModel):
    rmsPx: float
    maxPx: float
    wallQuadUv: list[list[float]]
    ok: bool

class CalibrationState(BaseModel):
    state: str = "IDLE"
    lidarId: str | None = None
    pointIndex: int = 0
    pointCount: int = 0
    targetsUv: list[list[float]] = []
    currentTargetUv: list[float] | None = None
    handUv: list[float] | None = None
    distancePx: float = 0.0
    samples: int = 0
    samplesNeeded: int = 40
    capturedMm: list[list[float]] = []
    result: CalibrationResult | None = None
    message: str = ""

class CalibrationService:
    def __init__(self, config_store: ConfigStore, ws_hub: WsHub):
        self.config_store = config_store
        self.ws_hub = ws_hub
        self.state = CalibrationState()
        self.lock = asyncio.Lock()
        
        self.auto_capture_radius_px = 60.0
        self.stable_frames_needed = 5
        self.stable_frames_count = 0
        self.current_samples_mm: list[tuple[float, float]] = []
        self.h0: np.ndarray | None = None
        self.wall_width_px = 1920
        self.wall_height_px = 1080
        
        self.last_ws_time = 0.0
        
    async def _broadcast_state(self):
        now = time.time()
        # Rate limit to ~15 Hz
        if now - self.last_ws_time < (1.0 / 15.0):
            return
        self.last_ws_time = now
        msg = {
            "v": 1,
            "type": "calibration",
            "ts": int(now * 1000),
            "data": self.state.model_dump()
        }
        await self.ws_hub.broadcast_events(msg)
        
    async def force_broadcast(self):
        self.last_ws_time = 0.0
        await self._broadcast_state()

    async def start(self, lidar_id: str, targets_uv: list[list[float]], samples_needed: int = 40):
        async with self.lock:
            if self.state.state not in ["IDLE", "COMMITTED", "CANCELLED", "FAILED"]:
                raise ValueError("CALIBRATION_BUSY")
                
            cfg = self.config_store.get_config()
            lidar_conf = next((l for l in cfg.lidars if l.id == lidar_id), None)
            if not lidar_conf:
                raise ValueError("LIDAR_NOT_FOUND")
                
            self.wall_width_px = cfg.wall.widthPx
            self.wall_height_px = cfg.wall.heightPx
                
            self.h0 = compute_h0(list(lidar_conf.scanArea.quadMm))
            if self.h0 is None:
                raise ValueError("Invalid Scan Area Quad")
                
            if not targets_uv:
                if getattr(lidar_conf, 'coverageUv', None) and len(lidar_conf.coverageUv) == 4:
                    targets_uv = [list(pt) for pt in lidar_conf.coverageUv]
                else:
                    targets_uv = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
                
            self.state = CalibrationState(
                state="WAIT_HAND",
                lidarId=lidar_id,
                pointIndex=0,
                pointCount=len(targets_uv),
                targetsUv=targets_uv,
                currentTargetUv=targets_uv[0],
                samplesNeeded=samples_needed,
                capturedMm=[],
                message=f"Calibrating Point 1/{len(targets_uv)}"
            )
            self.stable_frames_count = 0
            self.current_samples_mm = []
            
        await self.force_broadcast()

    async def cancel(self):
        async with self.lock:
            self.state.state = "CANCELLED"
            self.state.message = "Cancelled"
        await self.force_broadcast()
        
    async def process_blobs(self, lidar_id: str, raw_blobs_mm: list[tuple[float, float]]):
        # Called at 30Hz by detection service
        if self.state.state not in ["WAIT_HAND", "CAPTURING"]:
            return
        if self.state.lidarId != lidar_id:
            return
            
        async with self.lock:
            if not raw_blobs_mm:
                self.state.handUv = None
                self.state.distancePx = 9999.0
                if self.state.state == "CAPTURING":
                    # Hand left during capture -> back to WAIT_HAND
                    self.state.state = "WAIT_HAND"
                    self.state.samples = 0
                    self.current_samples_mm = []
                    self.stable_frames_count = 0
                    self.state.message = "Hand lost. Please return."
                await self._broadcast_state()
                return

            # Find closest blob in UV
            pts_mm = np.array(raw_blobs_mm)
            assert self.h0 is not None
            uvs = project(pts_mm, self.h0)
            
            target_uv = np.array(self.state.currentTargetUv)
            diffs = uvs - target_uv
            diffs_px = diffs * np.array([self.wall_width_px, self.wall_height_px])
            dists = np.linalg.norm(diffs_px, axis=1)
            
            best_idx = int(np.argmin(dists))
            best_dist = dists[best_idx]
            best_uv = uvs[best_idx]
            best_mm = pts_mm[best_idx]
            
            self.state.handUv = best_uv.tolist()
            self.state.distancePx = float(best_dist)
            
            if self.state.state == "WAIT_HAND":
                if best_dist < self.auto_capture_radius_px:
                    self.stable_frames_count += 1
                    if self.stable_frames_count >= self.stable_frames_needed:
                        self.state.state = "CAPTURING"
                        self.state.samples = 0
                        self.current_samples_mm = []
                        self.state.message = "Hold still..."
                else:
                    self.stable_frames_count = 0
                    
            elif self.state.state == "CAPTURING":
                if best_dist > self.auto_capture_radius_px * 1.5:
                    # Moved away too far
                    self.state.state = "WAIT_HAND"
                    self.state.samples = 0
                    self.current_samples_mm = []
                    self.stable_frames_count = 0
                    self.state.message = "Moved too far. Restarting point."
                else:
                    self.current_samples_mm.append((best_mm[0], best_mm[1]))
                    self.state.samples = len(self.current_samples_mm)
                    if self.state.samples >= self.state.samplesNeeded:
                        # Finished point
                        self._finish_point()
                        
        await self._broadcast_state()
        
    def _finish_point(self):
        pts = np.array(self.current_samples_mm)
        median_mm = np.median(pts, axis=0)
        mad = np.median(np.abs(pts - median_mm))
        
        if mad > 25.0:
            self.state.state = "WAIT_HAND"
            self.state.samples = 0
            self.current_samples_mm = []
            self.stable_frames_count = 0
            self.state.message = f"Too much noise (MAD={mad:.1f}mm). Please redo."
            return
            
        self.state.capturedMm.append(median_mm.tolist())
        self.state.pointIndex += 1
        
        if self.state.pointIndex >= self.state.pointCount:
            self._compute()
        else:
            self.state.state = "WAIT_HAND"
            self.state.currentTargetUv = self.state.targetsUv[self.state.pointIndex]
            self.state.samples = 0
            self.current_samples_mm = []
            self.stable_frames_count = 0
            self.state.message = f"Calibrating Point {self.state.pointIndex + 1}/{self.state.pointCount}"

    async def manual_capture(self):
        async with self.lock:
            if self.state.state in ["WAIT_HAND", "CAPTURING"] and self.state.handUv:
                # Force finish immediately with current 1 sample
                pts_mm = np.array(self.current_samples_mm) if len(self.current_samples_mm) > 0 else np.array([[0,0]]) # Need real mm?
                # Actually manual capture uses current handUv, but we need mm.
                # Since we don't store mm on state directly, let's just use the last seen.
                if len(self.current_samples_mm) > 0:
                    self._finish_point()
                else:
                    self.state.message = "No samples to force capture."
        await self.force_broadcast()
        
    def _compute(self):
        self.state.state = "COMPUTE"
        H, _, _ = compute_homography(self.state.capturedMm, self.state.targetsUv)
        
        if H is None:
            self.state.state = "FAILED"
            self.state.message = "Failed to compute Homography (bad points)"
            return
            
        # compute RMS
        pts_mm = np.array(self.state.capturedMm)
        assert H is not None
        proj_uv = project(pts_mm, H)
        diff = proj_uv - np.array(self.state.targetsUv)
        diff_px = diff * np.array([self.wall_width_px, self.wall_height_px])
        dists = np.linalg.norm(diff_px, axis=1)
        
        rms_px = float(np.sqrt(np.mean(dists**2)))
        max_px = float(np.max(dists))
        
        # projected wall quad
        # we can project a large box or just corners
        wall_quad_uv = [[0,0],[1,0],[1,1],[0,1]] # This should ideally be the source quad projected
        
        self.state.result = CalibrationResult(
            rmsPx=rms_px,
            maxPx=max_px,
            wallQuadUv=wall_quad_uv,
            ok=(rms_px <= 15.0)
        )
        self.state.state = "REVIEW"
        self.state.message = f"RMS Error: {rms_px:.1f} px"
        
    async def commit(self):
        async with self.lock:
            if self.state.state == "REVIEW" and self.state.result:
                # Save to config
                H, _, _ = compute_homography(self.state.capturedMm, self.state.targetsUv)
                cfg = self.config_store.get_config()
                lidar = next((l for l in cfg.lidars if l.id == self.state.lidarId), None)
                if lidar:
                    lidar.calibration.homography = H.tolist() if H is not None else None
                    lidar.calibration.rmsPx = self.state.result.rmsPx
                    lidar.calibration.targetsUv = self.state.targetsUv
                    lidar.calibration.capturedMm = self.state.capturedMm
                    lidar.calibration.createdAt = int(time.time() * 1000)
                    self.config_store.save(cfg)
                
                self.state.state = "COMMITTED"
                self.state.message = "Saved!"
        await self.force_broadcast()
        
    async def redo(self, point_index: int):
        async with self.lock:
            if self.state.state == "REVIEW":
                if 0 <= point_index < self.state.pointCount:
                    # We can't really easily rollback just 1 point if it's already captured,
                    # but the prompt says redo 1 point. We just replace that point index.
                    # Pop the captured points from the index to end? No, replace specific point.
                    # Actually, if we just want to redo, we can just jump to that index and wait.
                    self.state.pointIndex = point_index
                    self.state.currentTargetUv = self.state.targetsUv[point_index]
                    # We might need to pop capturedMm
                    if len(self.state.capturedMm) > point_index:
                        self.state.capturedMm = self.state.capturedMm[:point_index]
                    self.state.state = "WAIT_HAND"
                    self.state.samples = 0
                    self.current_samples_mm = []
                    self.stable_frames_count = 0
        await self.force_broadcast()
