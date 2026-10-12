import asyncio
import logging
import time

import numpy as np
from pydantic import BaseModel

from app.core.homography import compute_h0, compute_homography, project
from app.services.ws_hub import WsHub
from app.storage.config_store import ConfigStore

logger = logging.getLogger(__name__)


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
    hasValidTouch: bool = False
    samples: int = 0
    samplesNeeded: int = 30
    progressPct: int = 0
    savedPoints: list[int] = []
    capturedMm: list[list[float]] = []
    result: CalibrationResult | None = None
    message: str = ""

class CalibrationService:
    def __init__(self, config_store: ConfigStore, ws_hub: WsHub):
        self.config_store = config_store
        self.ws_hub = ws_hub
        self.state = CalibrationState()
        self.lock = asyncio.Lock()
        
        self.auto_capture_radius_px = 350.0
        self.stable_frames_needed = 3
        self.stable_frames_count = 0
        self.current_samples_mm: list[tuple[float, float]] = []
        self.last_seen_mm: tuple[float, float] | None = None
        self.h0: np.ndarray | None = None
        self.wall_width_px = 1920
        self.wall_height_px = 1080
        
        self.last_ws_time = 0.0
        self.missing_frames_count = 0
        
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

    async def start(self, lidar_id: str, targets_uv: list[list[float]], samples_needed: int = 25):
        async with self.lock:
            # If already active, restart cleanly instead of raising 409 Conflict
            if self.state.state not in ["IDLE", "COMMITTED", "CANCELLED", "FAILED"]:
                logger.info(f"Restarting calibration for lidar {lidar_id} (previous state: {self.state.state})")
                
            cfg = self.config_store.get_config()
            lidar_conf = next((l for l in cfg.lidars if l.id == lidar_id), None)
            if not lidar_conf:
                raise ValueError("LIDAR_NOT_FOUND")
                
            self.wall_width_px = cfg.wall.widthPx
            self.wall_height_px = cfg.wall.heightPx
                
            # Determine initial projection H0
            cal_h = None
            if getattr(lidar_conf, 'calibration', None) and getattr(lidar_conf.calibration, 'homography', None):
                try:
                    H_saved = np.array(lidar_conf.calibration.homography, dtype=np.float32)
                    if H_saved.shape == (3, 3) and np.linalg.matrix_rank(H_saved) == 3:
                        cal_h = H_saved
                        logger.info(f"Using previous homography as initial H0 for lidar {lidar_id}")
                except Exception:
                    pass

            if cal_h is not None:
                self.h0 = cal_h
            else:
                quad_mm = list(lidar_conf.scanArea.quadMm) if lidar_conf.scanArea.quadMm else []
                is_valid_quad = False
                if len(quad_mm) == 4:
                    w = np.linalg.norm(np.array(quad_mm[1]) - np.array(quad_mm[0]))
                    h = np.linalg.norm(np.array(quad_mm[3]) - np.array(quad_mm[0]))
                    if w >= 800.0 and h >= 600.0:
                        is_valid_quad = True

                if is_valid_quad:
                    self.h0 = compute_h0(quad_mm)
                else:
                    self.h0 = compute_h0([[-2500, 3500], [2500, 3500], [2500, 200], [-2500, 200]])
                
            if not targets_uv:
                if getattr(lidar_conf, 'coverageUv', None) and len(lidar_conf.coverageUv) == 4:
                    targets_uv = [list(pt) for pt in lidar_conf.coverageUv]
                else:
                    targets_uv = [[0.2, 0.25], [0.8, 0.25], [0.8, 0.75], [0.2, 0.75]]
                
            self.state = CalibrationState(
                state="WAIT_HAND",
                lidarId=lidar_id,
                pointIndex=0,
                pointCount=len(targets_uv),
                targetsUv=targets_uv,
                currentTargetUv=targets_uv[0],
                hasValidTouch=False,
                distancePx=9999.0,
                samplesNeeded=samples_needed,
                progressPct=0,
                savedPoints=[],
                capturedMm=[],
                message="ĐIỂM 1 / 4 (Góc Trên - Trái): Hãy chạm tay vào Điểm 1 rồi bấm [Space]"
            )
            self.stable_frames_count = 0
            self.current_samples_mm = []
            self.last_seen_mm = None
            self.missing_frames_count = 0
            
        await self.force_broadcast()

    async def cancel(self):
        async with self.lock:
            self.state.state = "CANCELLED"
            self.state.message = "Đã hủy hiệu chuẩn"
        await self.force_broadcast()
        
    async def process_blobs(self, lidar_id: str, raw_blobs_mm: list[tuple[float, float]]):
        # Called at 30Hz by detection service
        if self.state.state not in ["WAIT_HAND", "CAPTURING", "POINT_SAVED"]:
            return
        if self.state.lidarId != lidar_id:
            return
            
        async with self.lock:
            if not raw_blobs_mm:
                self.state.hasValidTouch = False
                self.state.handUv = None
                self.state.distancePx = 9999.0
                self.last_seen_mm = None
                if self.state.state == "CAPTURING":
                    self.missing_frames_count = getattr(self, 'missing_frames_count', 0) + 1
                    if self.missing_frames_count > 15:
                        self.missing_frames_count = 0
                        self.state.state = "WAIT_HAND"
                        self.state.samples = 0
                        self.state.progressPct = 0
                        self.current_samples_mm = []
                        self.state.message = f"Mất dấu điểm chạm! Hãy chạm lại vào Điểm {self.state.pointIndex + 1} rồi bấm Space."
                elif self.state.state == "WAIT_HAND":
                    self.state.message = f"🔴 Chưa thấy tọa độ LiDAR! Hãy chạm tay vào Điểm {self.state.pointIndex + 1}."
                await self._broadcast_state()
                return

            pts_mm = np.array(raw_blobs_mm)
            
            # Filter candidates that are not right on top of previously captured points
            valid_candidates = []
            if len(self.state.capturedMm) > 0:
                prev_pts = np.array(self.state.capturedMm)
                for pt in pts_mm:
                    dists_to_prev = np.linalg.norm(prev_pts - pt, axis=1)
                    if np.all(dists_to_prev >= 250.0):
                        valid_candidates.append(pt)
                if not valid_candidates:
                    valid_candidates = pts_mm.tolist()
            else:
                valid_candidates = pts_mm.tolist()

            cand_arr = np.array(valid_candidates)
            
            # Project candidates to UV space
            if self.h0 is not None:
                try:
                    cand_uvs = project(cand_arr, self.h0)
                except Exception:
                    cand_uvs = np.zeros((len(cand_arr), 2))
            else:
                cand_uvs = np.zeros((len(cand_arr), 2))

            target_uv = np.array(self.state.currentTargetUv if self.state.currentTargetUv else [0.5, 0.5])
            
            # Distance in screen pixels to current target
            diff_px = (cand_uvs - target_uv) * np.array([self.wall_width_px, self.wall_height_px])
            dists_px = np.linalg.norm(diff_px, axis=1)
            
            best_idx = int(np.argmin(dists_px))
            best_mm = valid_candidates[best_idx]
            best_uv = cand_uvs[best_idx]
            min_dist_px = float(dists_px[best_idx])
            
            # Live tracking coordinate
            self.state.handUv = [float(best_uv[0]), float(best_uv[1])]
            self.state.distancePx = min_dist_px
            
            # Strict touch validation: must be within 400px of the calibration target
            TOUCH_VALID_RADIUS_PX = 400.0
            
            if min_dist_px <= TOUCH_VALID_RADIUS_PX:
                self.state.hasValidTouch = True
                self.last_seen_mm = (float(best_mm[0]), float(best_mm[1]))
                self.missing_frames_count = 0
            else:
                self.state.hasValidTouch = False
                self.last_seen_mm = None

            if self.state.state == "WAIT_HAND":
                if self.state.hasValidTouch:
                    self.state.message = f"🟢 ĐÃ BẮT ĐIỂM {self.state.pointIndex + 1} ({int(min_dist_px)}px)! Bấm [Space] để lấy mẫu."
                else:
                    self.state.message = f"🔴 Chưa thấy điểm chạm tại Điểm {self.state.pointIndex + 1}! Hãy chạm tay vào mục tiêu (Khoảng cách: {int(min_dist_px)}px)."
            elif self.state.state == "CAPTURING":
                if self.state.hasValidTouch and self.last_seen_mm is not None:
                    self.current_samples_mm.append(self.last_seen_mm)
                    self.state.samples = len(self.current_samples_mm)
                    self.state.progressPct = min(100, int((self.state.samples / self.state.samplesNeeded) * 100))
                    self.state.message = f"⏳ Đang lấy mẫu Điểm {self.state.pointIndex + 1}: {self.state.progressPct}% - Giữ yên vị trí..."
                    
                    if self.state.samples >= self.state.samplesNeeded:
                        self._finish_point()
                else:
                    self.missing_frames_count = getattr(self, 'missing_frames_count', 0) + 1
                    if self.missing_frames_count > 15:
                        self.missing_frames_count = 0
                        self.state.state = "WAIT_HAND"
                        self.state.samples = 0
                        self.state.progressPct = 0
                        self.current_samples_mm = []
                        self.state.message = f"Mất dấu điểm chạm! Hãy chạm lại vào Điểm {self.state.pointIndex + 1} rồi bấm Space."
                        
        await self._broadcast_state()
        
    def _finish_point(self):
        if not self.current_samples_mm:
            return
            
        pts = np.array(self.current_samples_mm)
        median_mm = np.median(pts, axis=0)
        
        self.state.capturedMm.append([float(median_mm[0]), float(median_mm[1])])
        self.state.savedPoints.append(self.state.pointIndex)
        self.state.progressPct = 100
        saved_num = self.state.pointIndex + 1
        
        if len(self.state.capturedMm) >= self.state.pointCount:
            self._compute()
        else:
            self.state.state = "POINT_SAVED"
            self.state.hasValidTouch = False
            self.state.message = f"✓ ĐÃ LƯU ĐIỂM {saved_num}! Bấm [Space] để chuyển sang Điểm {saved_num + 1}."

    async def manual_capture(self):
        async with self.lock:
            if self.state.state == "POINT_SAVED":
                # Advance to next point
                if self.state.pointIndex + 1 < self.state.pointCount:
                    self.state.pointIndex += 1
                    self.state.currentTargetUv = self.state.targetsUv[self.state.pointIndex]
                    self.state.samples = 0
                    self.state.progressPct = 0
                    self.current_samples_mm = []
                    self.last_seen_mm = None
                    self.state.hasValidTouch = False
                    self.state.state = "WAIT_HAND"
                    self.state.message = f"👉 Hãy chạm vào Điểm {self.state.pointIndex + 1} rồi bấm [Space]"
                else:
                    self._compute()
            elif self.state.state == "WAIT_HAND":
                # CRITICAL: Do NOT capture unless there is a real coordinate at the target point!
                if not self.state.hasValidTouch or self.last_seen_mm is None:
                    self.state.message = f"⚠ KHÔNG THỂ LẤY ĐIỂM! Chưa có tọa độ trả về tại Điểm {self.state.pointIndex + 1}. Hãy chạm tay vào vòng tròn mục tiêu!"
                    await self.force_broadcast()
                    return

                if len(self.state.capturedMm) > 0:
                    prev_pts = np.array(self.state.capturedMm)
                    dists = np.linalg.norm(prev_pts - np.array(self.last_seen_mm), axis=1)
                    if np.any(dists < 250.0):
                        self.state.message = f"⚠ Điểm này quá gần Điểm đã lưu! Hãy chạm vào góc Điểm {self.state.pointIndex + 1}."
                        await self.force_broadcast()
                        return
                
                self.state.state = "CAPTURING"
                self.current_samples_mm = [self.last_seen_mm]
                self.state.samples = 1
                self.state.progressPct = int(100 / self.state.samplesNeeded)
                self.state.message = f"⏳ Đang lấy mẫu Điểm {self.state.pointIndex + 1}... Giữ yên vị trí!"
            elif self.state.state == "CAPTURING":
                # Instant finish if already has sufficient samples
                if len(self.current_samples_mm) >= 5:
                    self._finish_point()
                    
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
                try:
                    # Save to config
                    H, _, _ = compute_homography(self.state.capturedMm, self.state.targetsUv)
                    cfg = self.config_store.get_config()
                    lidar = next((l for l in cfg.lidars if l.id == self.state.lidarId), None)
                    if lidar and H is not None:
                        lidar.calibration.homography = H.tolist()
                        lidar.calibration.rmsPx = self.state.result.rmsPx
                        lidar.calibration.targetsUv = self.state.targetsUv
                        lidar.calibration.capturedMm = self.state.capturedMm
                        lidar.calibration.createdAt = int(time.time() * 1000)

                        # Automatically update scanArea.quadMm to cover calibrated projection wall
                        try:
                            H_inv = np.linalg.inv(H)
                            margin = 0.15 # 15% margin to ensure interactive area has breathing room
                            corners_uv = np.array([
                                [-margin, -margin],
                                [1.0 + margin, -margin],
                                [1.0 + margin, 1.0 + margin],
                                [-margin, 1.0 + margin]
                            ], dtype=np.float32)
                            wall_quad_mm = project(corners_uv, H_inv)
                            w_mm = float(np.linalg.norm(wall_quad_mm[1] - wall_quad_mm[0]))
                            h_mm = float(np.linalg.norm(wall_quad_mm[3] - wall_quad_mm[0]))
                            if 800.0 <= w_mm <= 15000.0 and 600.0 <= h_mm <= 15000.0:
                                lidar.scanArea.quadMm = tuple((float(p[0]), float(p[1])) for p in wall_quad_mm)
                                lidar.coverageUv = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
                                logger.info(f"Updated scanArea.quadMm to {w_mm:.0f}x{h_mm:.0f}mm for lidar {self.state.lidarId}")
                            else:
                                logger.warning(f"Derived wall quad size ({w_mm:.0f}x{h_mm:.0f}mm) is outside physical bounds. Keeping existing scanArea.")
                        except Exception as quad_err:
                            logger.warning(f"Could not derive scanArea from H_inv: {quad_err}")

                        self.config_store.save(cfg)
                        logger.info(f"Calibration successfully saved to config for lidar {self.state.lidarId}")

                    self.state.state = "COMMITTED"
                    self.state.message = "Đã lưu thành công!"
                except Exception as e:
                    logger.error(f"Error in calibration commit: {e}", exc_info=True)
                    self.state.message = f"Lỗi lưu cấu hình: {e}"
                    raise e
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
