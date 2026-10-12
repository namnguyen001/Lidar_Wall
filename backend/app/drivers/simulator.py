import math
import threading
import time

import numpy as np

from app.drivers.base import DriverStatus, LidarDriver, ScanFrame


class SimulatorDriver(LidarDriver):
    def __init__(self, seed: int = 1, hands: int = 1):
        self.seed = seed
        self.hands = min(max(hands, 0), 3)
        self.status = DriverStatus()
        self._latest_frame: ScanFrame | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        np.random.seed(seed)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.status.state = "connecting"
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self.status.state = "disconnected"

    def get_status(self) -> DriverStatus:
        return self.status

    def get_latest_frame(self) -> ScanFrame | None:
        return self._latest_frame

    def _run(self):
        time.sleep(0.5)  # simulate connection delay
        self.status.state = "connected"
        last_time = time.perf_counter()
        
        while not self._stop_event.is_set():
            now = time.perf_counter()
            dt = now - last_time
            if dt >= 0.1:  # 10 Hz
                last_time = now
                self._generate_frame(now)
                self.status.scan_count += 1
                self.status.fps = 1.0 / dt
            else:
                time.sleep(0.01)

    def _generate_frame(self, t: float):
        # Wall at y = 1000, from x = -2000 to x = 2000
        x_wall = np.linspace(-2000, 2000, 800)
        y_wall = np.full_like(x_wall, 1000.0)
        
        points = np.column_stack((x_wall, y_wall))
        
        # Add hands
        for i in range(self.hands):
            hx = math.sin(t + i*2) * 500
            hy = 950 + math.cos(t * 2 + i) * 30
            
            # hand shape
            ang = np.linspace(0, np.pi, 20)
            hx_pts = hx + np.cos(ang) * 40
            hy_pts = hy + np.sin(ang) * 40
            hand_pts = np.column_stack((hx_pts, hy_pts))
            points = np.vstack((points, hand_pts))
            
        # Add noise
        noise = np.random.normal(0, 5, points.shape)
        points += noise
        
        self._latest_frame = ScanFrame(points=points.astype(np.float32), timestamp=t)
