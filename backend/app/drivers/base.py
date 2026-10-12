from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class ScanFrame:
    points: np.ndarray  # shape (N, 2), float32, x y in mm
    timestamp: float

@dataclass
class DriverStatus:
    state: str = "disconnected" # "disconnected", "connecting", "connected", "error"
    fps: float = 0.0
    scan_count: int = 0
    last_error: str | None = None

class LidarDriver(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def get_status(self) -> DriverStatus: ...
    def get_latest_frame(self) -> ScanFrame | None: ...
