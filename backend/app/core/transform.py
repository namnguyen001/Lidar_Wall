import math

import numpy as np


def apply_transform(x: np.ndarray, y: np.ndarray, flip_x: bool, flip_y: bool, rotation_deg: float, offset_mm: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    """
    Applies transformation in specific order: flipX, flipY, rotation, offset.
    x, y are numpy arrays of shape (N,).
    Returns (x_out, y_out).
    """
    # 1. Flip
    if flip_x:
        x = -x
    if flip_y:
        y = -y
        
    # 2. Rotation
    if rotation_deg != 0.0:
        rad = math.radians(rotation_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a
        x, y = x_rot, y_rot
        
    # 3. Offset
    ox, oy = offset_mm
    if ox != 0.0:
        x = x + ox
    if oy != 0.0:
        y = y + oy
        
    return x, y
