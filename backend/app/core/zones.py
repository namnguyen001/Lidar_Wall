import numpy as np

def hit_test_rect(u: float, v: float, rect: dict, hysteresis_uv: float = 0.0, currently_inside: bool = False) -> bool:
    x, y, w, h = rect['x'], rect['y'], rect['w'], rect['h']
    
    # If currently inside, we expand the rect by hysteresis to prevent flicker on exit
    margin = hysteresis_uv if currently_inside else 0.0
    
    return (x - margin <= u <= x + w + margin) and (y - margin <= v <= y + h + margin)

def hit_test_circle(u: float, v: float, circle: dict, wall_width_px: float, wall_height_px: float, hysteresis_uv: float = 0.0, currently_inside: bool = False) -> bool:
    cx, cy, r = circle['cx'], circle['cy'], circle['r']
    
    dx_px = (u - cx) * wall_width_px
    dy_px = (v - cy) * wall_height_px
    
    # r is a fraction of wall width
    r_px = r * wall_width_px
    
    margin_px = (hysteresis_uv * wall_width_px) if currently_inside else 0.0
    
    return (dx_px**2 + dy_px**2) <= (r_px + margin_px)**2

def hit_test_polygon(u: float, v: float, polygon: dict, hysteresis_uv: float = 0.0, currently_inside: bool = False) -> bool:
    points = polygon['points']
    n = len(points)
    if n < 3:
        return False
        
    inside = False
    p1u, p1v = points[0]
    for i in range(n + 1):
        p2u, p2v = points[i % n]
        if v > min(p1v, p2v):
            if v <= max(p1v, p2v):
                if u <= max(p1u, p2u):
                    if p1v != p2v:
                        xints = (v - p1v) * (p2u - p1u) / (p2v - p1v) + p1u
                    if p1u == p2u or u <= xints:
                        inside = not inside
        p1u, p1v = p2u, p2v
        
    if currently_inside and not inside and hysteresis_uv > 0:
        # Distance to line segment check for hysteresis is complex.
        # Approximation: if we are outside but were inside, check if we are within hysteresis_uv of any segment
        for i in range(n):
            p1 = np.array(points[i])
            p2 = np.array(points[(i+1)%n])
            p = np.array([u, v])
            
            l2 = np.sum((p1 - p2)**2)
            if l2 == 0:
                dist = np.linalg.norm(p - p1)
            else:
                t = max(0, min(1, np.dot(p - p1, p2 - p1) / l2))
                projection = p1 + t * (p2 - p1)
                dist = np.linalg.norm(p - projection)
                
            if dist <= hysteresis_uv:
                return True
                
    return inside

def validate_polygon(points: list[tuple[float, float]]) -> bool:
    if len(points) < 3:
        return False
        
    # Check self-intersection (O(n^2) naive)
    def ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    def intersect(A, B, C, D):
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)
        
    n = len(points)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue # Adjacent segments
            if intersect(points[i], points[(i+1)%n], points[j], points[(j+1)%n]):
                return False
                
    return True
