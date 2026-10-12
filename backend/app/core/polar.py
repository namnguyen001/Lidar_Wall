import numpy as np


def polar_to_xy(angles_rad: np.ndarray, ranges_mm: np.ndarray, min_range_mm: float, max_range_mm: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Converts polar coordinates (angles_rad, ranges_mm) to cartesian (X, Y) in mm.
    Filters out points with range <= 0 or outside [min_range_mm, max_range_mm].
    Returns (x: np.ndarray, y: np.ndarray, valid_mask: np.ndarray).
    """
    valid_mask = (ranges_mm > 0) & (ranges_mm >= min_range_mm) & (ranges_mm <= max_range_mm) & ~np.isnan(ranges_mm)
    
    r_valid = ranges_mm[valid_mask]
    a_valid = angles_rad[valid_mask]
    
    # x = r * sin(theta), y = r * cos(theta) according to typical YDLidar orientation, 
    # but math convention: x = r * cos(theta), y = r * sin(theta). 
    # The prompt says: "Lidar space (mm): gốc tại tâm lidar; x sang phải, y hướng ra phía trước (sau flip/rotation do người dùng chỉnh)."
    # Let's stick to x = r*cos(a), y = r*sin(a) or vice-versa?
    # Test01.py used: x = r * sin(a), y = r * cos(a). We'll use this.
    x = r_valid * np.sin(a_valid)
    y = r_valid * np.cos(a_valid)
    
    return x, y, valid_mask
