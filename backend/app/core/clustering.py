
import numpy as np


def cluster_points(x: np.ndarray, y: np.ndarray, angles_rad: np.ndarray, 
                   cluster_gap_mm: float = 80.0, min_points: int = 2,
                   min_size_mm: float = 30.0, max_size_mm: float = 300.0) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[list[int]]]:
    """
    Clusters points based on Euclidean distance gap along sorted angles.
    Returns:
      centroids_x: array of float
      centroids_y: array of float
      sizes_mm: array of float
      clusters_indices: list of lists containing the indices of original points for each valid cluster
    """
    if len(x) == 0:
        return np.array([]), np.array([]), np.array([]), []
        
    # 1. Sort by angle
    sort_idx = np.argsort(angles_rad)
    x_s = x[sort_idx]
    y_s = y[sort_idx]
    
    # 2. Find gaps
    # Calculate euclidean distance between consecutive points
    dx = np.diff(x_s)
    dy = np.diff(y_s)
    dists = np.sqrt(dx*dx + dy*dy)
    
    # Also wrap-around: from last point to first point, if they are close in angle?
    # Usually lidars spin 360, so last point and first point might be adjacent.
    # But for a wall, we often just scan a segment. We'll ignore wrap-around for simplicity unless needed.
    
    # A gap is where distance > cluster_gap_mm
    gap_indices = np.where(dists > cluster_gap_mm)[0] + 1
    
    # Split indices into clusters
    cluster_splits = np.split(np.arange(len(x_s)), gap_indices)
    
    centroids_x = []
    centroids_y = []
    sizes_mm = []
    clusters_indices = []
    
    for split in cluster_splits:
        if len(split) < min_points:
            continue
            
        # Get points for this cluster
        cx = x_s[split]
        cy = y_s[split]
        
        # Extent = max distance between any two points in the cluster
        # Fast approximation for extent of a line-like cluster: distance from first to last point
        # Or more accurately, max bounding box or max pairwise distance.
        # Since points are ordered by angle, dist(first, last) is a good approximation of size.
        size = np.sqrt((cx[-1] - cx[0])**2 + (cy[-1] - cy[0])**2)
        
        # Even better for small clusters: max distance from centroid, etc.
        # But for wall touch, size is exactly the width.
        
        if min_size_mm <= size <= max_size_mm:
            centroids_x.append(np.mean(cx))
            centroids_y.append(np.mean(cy))
            sizes_mm.append(size)
            # Map back to original indices
            clusters_indices.append(sort_idx[split].tolist())
            
    return np.array(centroids_x), np.array(centroids_y), np.array(sizes_mm), clusters_indices
