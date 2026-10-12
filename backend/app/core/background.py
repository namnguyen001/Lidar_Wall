import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

class BackgroundModel:
    def __init__(self, lidar_id: str, learn_scans: int = 60, tolerance_mm: float = 40.0):
        self.lidar_id = lidar_id
        self.learn_scans = learn_scans
        self.tolerance_mm = tolerance_mm
        
        # 360 degrees / 0.5 deg resolution = 720 bins
        self.bin_resolution_deg = 0.5
        self.num_bins = int(360.0 / self.bin_resolution_deg)
        
        # We store the learned background median ranges
        # shape: (num_bins,)
        self.bg_ranges: np.ndarray | None = None
        
        # Learning state
        self.is_learning = False
        self.learning_buffer: list[np.ndarray] = [] # stores arrays of size (num_bins,) for each scan
        self.learned_at: float | None = None
        
    def get_bin_indices(self, angles_rad: np.ndarray) -> np.ndarray:
        """Convert angles in radians to bin indices 0..719"""
        # Ensure angles are in [0, 2*pi)
        a_mod = np.mod(angles_rad, 2 * np.pi)
        a_deg = np.degrees(a_mod)
        
        indices = np.floor(a_deg / self.bin_resolution_deg).astype(int)
        # clip just in case
        return np.clip(indices, 0, self.num_bins - 1)

    def start_learning(self):
        self.is_learning = True
        self.learning_buffer = []
        self.learned_at = None
        logger.info(f"[{self.lidar_id}] Started learning background ({self.learn_scans} scans)")

    def process_learning_scan(self, angles_rad: np.ndarray, ranges_mm: np.ndarray) -> bool:
        """
        Feed a scan into the learning buffer.
        Returns True if learning has just finished.
        """
        if not self.is_learning:
            return False
            
        bins = self.get_bin_indices(angles_rad)
        
        # For a single scan, multiple points might fall into the same bin.
        # We take the minimum range for that bin in this scan to be conservative,
        # or just average. Let's do minimum range since background is usually the furthest object, 
        # wait - no, background is the wall. We take median over scans.
        # Within one scan, we can just scatter-min or take the first.
        # Numpy doesn't have a direct scatter-min without a loop or np.minimum.at
        
        scan_bg = np.full(self.num_bins, np.nan)
        # np.minimum.at ignores nan if we handle it carefully, but it's simpler to do:
        # Sort by range descending, then assignment will keep the smallest (since later overwrites)
        sort_idx = np.argsort(ranges_mm)[::-1]
        scan_bg[bins[sort_idx]] = ranges_mm[sort_idx]
        
        self.learning_buffer.append(scan_bg)
        
        if len(self.learning_buffer) >= self.learn_scans:
            self._finish_learning()
            return True
            
        return False

    def _finish_learning(self):
        # We have a list of arrays (scans, num_bins)
        all_scans = np.vstack(self.learning_buffer) # shape: (learn_scans, num_bins)
        
        # Calculate median ignoring NaNs
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            self.bg_ranges = np.nanmedian(all_scans, axis=0)
            
        # For bins that never saw a point (all NaN), set to a large number so nothing is considered foreground there?
        # Or set to 0 so everything is foreground? If we set to large, any point will be < bg. So it will be foreground.
        # Actually, if there's no background, any new point is foreground. So set to Infinity.
        self.bg_ranges[np.isnan(self.bg_ranges)] = np.inf
        
        self.is_learning = False
        import time
        self.learned_at = time.time()
        logger.info(f"[{self.lidar_id}] Finished learning background.")

    def get_foreground_mask(self, angles_rad: np.ndarray, ranges_mm: np.ndarray) -> np.ndarray:
        """
        Returns boolean mask where point is foreground (range < bg - tolerance)
        """
        if self.bg_ranges is None:
            # If not learned, everything is foreground
            return np.ones_like(ranges_mm, dtype=bool)
            
        bins = self.get_bin_indices(angles_rad)
        bg_for_pts = self.bg_ranges[bins]
        
        # Point is foreground if it is closer than background minus tolerance
        mask = ranges_mm < (bg_for_pts - self.tolerance_mm)
        return mask

    def load(self, file_path: str) -> bool:
        if os.path.exists(file_path):
            try:
                self.bg_ranges = np.load(file_path)
                if self.bg_ranges.shape == (self.num_bins,):
                    logger.info(f"[{self.lidar_id}] Loaded background from {file_path}")
                    return True
            except Exception as e:
                logger.error(f"[{self.lidar_id}] Failed to load background: {e}")
        self.bg_ranges = None
        return False
        
    def save(self, file_path: str):
        if self.bg_ranges is not None:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            np.save(file_path, self.bg_ranges)
            logger.info(f"[{self.lidar_id}] Saved background to {file_path}")
