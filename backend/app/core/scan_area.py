
import numpy as np


def is_convex_quad(quad: list[tuple[float, float]]) -> bool:
    """
    Checks if a given quad (4 points) is strictly convex.
    Uses cross product of consecutive edges.
    """
    if len(quad) != 4:
        return False
        
    pts = np.array(quad)
    # edges: p1-p0, p2-p1, p3-p2, p0-p3
    edges = np.roll(pts, -1, axis=0) - pts
    # cross product of consecutive edges
    cross_prods = np.cross(edges, np.roll(edges, -1, axis=0))
    
    # All cross products must have the same sign (all positive or all negative)
    # strictly convex means cross product != 0
    if np.all(cross_prods > 0) or np.all(cross_prods < 0):
        return True
    return False

def filter_inside_quad(x: np.ndarray, y: np.ndarray, quad: list[tuple[float, float]]) -> np.ndarray:
    """
    Vectorized check if points (x,y) are inside a convex quad.
    Returns boolean mask of same shape as x and y.
    """
    if len(x) == 0:
        return np.zeros_like(x, dtype=bool)
        
    pts = np.column_stack((x, y))
    quad_pts = np.array(quad)
    
    # We check if point is on the same side of all 4 directed edges
    # edge vectors
    edges = np.roll(quad_pts, -1, axis=0) - quad_pts
    
    # To check all points against all edges efficiently:
    # edge i is quad_pts[i] to quad_pts[i+1]
    # point vector is pts - quad_pts[i]
    # We need cross product: edge_x * pt_y - edge_y * pt_x
    
    mask = np.ones(len(pts), dtype=bool)
    
    # Determine reference sign from the polygon itself (to handle CW vs CCW)
    cross_poly = np.cross(edges[0], edges[1])
    sign = 1 if cross_poly > 0 else -1
    
    for i in range(4):
        p0 = quad_pts[i]
        edge = edges[i]
        
        pt_vecs = pts - p0
        # cross2d = x1*y2 - y1*x2
        # edge = (edge[0], edge[1])
        # pt_vecs = (pt_vecs[:,0], pt_vecs[:,1])
        cross = edge[0] * pt_vecs[:, 1] - edge[1] * pt_vecs[:, 0]
        
        # If sign is positive, point should have cross >= 0
        if sign > 0:
            mask &= (cross >= 0)
        else:
            mask &= (cross <= 0)
            
    return mask
