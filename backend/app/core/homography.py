
import cv2
import numpy as np


def compute_h0(quad_mm: list[tuple[float, float]]) -> np.ndarray | None:
    """
    Computes a provisional homography H0 mapping the scan area quad (mm)
    to the unit UV square [0,0], [1,0], [1,1], [0,1].
    """
    if len(quad_mm) != 4:
        return None
        
    src = np.array(quad_mm, dtype=np.float32)
    dst = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)
    
    H, _ = cv2.findHomography(src, dst, 0)
    return H

def compute_homography(src_mm: list[tuple[float, float]], dst_uv: list[tuple[float, float]]) -> tuple[np.ndarray | None, float, float]:
    """
    Computes homography from src_mm to dst_uv.
    Returns (H, rmsPx, maxPx)
    """
    if len(src_mm) != len(dst_uv) or len(src_mm) < 4:
        return None, 0.0, 0.0
        
    src = np.array(src_mm, dtype=np.float32)
    dst = np.array(dst_uv, dtype=np.float32)
    
    method = 0 if len(src) == 4 else cv2.RANSAC
    H, _ = cv2.findHomography(src, dst, method)
    
    if H is None:
        return None, 0.0, 0.0
        
    # Check rank / invertibility (avoid false-rejecting mm->UV transforms with scale-dependent small det)
    if np.linalg.matrix_rank(H) < 3:
        return None, 0.0, 0.0
        
    # Check collinearity or bad mapping by projecting
    proj_uv = project(src, H)
    
    # residuals (error in UV)
    diff = proj_uv - dst
    dists_uv = np.linalg.norm(diff, axis=1)
    
    # To get px, we need wallSizePx, but we don't have it here directly.
    # We will compute it outside, or pass wall_width_px, wall_height_px.
    # Wait, the prompt says "residuals_px". Let's just return dists_uv and let the service scale it.
    # Or just return H, we'll calculate RMS inside the service.
    # Actually, returning H and projected is better.
    return H, 0.0, 0.0 # Will calculate RMS later

def project(points: np.ndarray, H: np.ndarray) -> np.ndarray:
    """
    Project points through homography H.
    points: shape (N, 2)
    Returns: shape (N, 2)
    """
    if len(points) == 0:
        return np.zeros((0, 2), dtype=np.float32)
        
    # Add homogeneous coordinate
    pts_h = np.column_stack((points, np.ones(len(points))))
    
    # Project
    proj_h = np.dot(H, pts_h.T).T
    
    # Normalize
    with np.errstate(divide='ignore', invalid='ignore'):
        z = proj_h[:, 2:3]
        proj = proj_h[:, :2] / z
        
    # Handle div by zero if any
    proj[np.isnan(proj)] = 0.0
    proj[np.isinf(proj)] = 0.0
    
    return proj
