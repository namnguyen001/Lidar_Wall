import math

import numpy as np

from app.core.background import BackgroundModel
from app.core.clustering import cluster_points
from app.core.polar import polar_to_xy
from app.core.scan_area import filter_inside_quad, is_convex_quad
from app.core.tracking import Tracker
from app.core.transform import apply_transform


def test_polar_to_xy():
    angles = np.array([0, math.pi/2, math.pi, -math.pi/2, 0])
    ranges = np.array([100, 200, 300, 400, 0])  # r=0 should be dropped
    
    x, y, mask = polar_to_xy(angles, ranges, 10, 500)
    
    assert len(x) == 4
    # expected x: [0, 200, 0, -400] -> Wait: x = r*sin(a) according to our implementation
    # Let's check polar.py: x = r * sin(a), y = r * cos(a)
    assert np.allclose(x, [0, 200, 0, -400], atol=1e-5)
    assert np.allclose(y, [100, 0, -300, 0], atol=1e-5)

def test_apply_transform():
    x = np.array([100.0, 200.0])
    y = np.array([50.0, -50.0])
    
    # Flip X
    x1, y1 = apply_transform(x, y, True, False, 0.0, (0.0, 0.0))
    assert np.allclose(x1, [-100, -200])
    assert np.allclose(y1, [50, -50])
    
    # Rotation 90 deg (ccw)
    x2, y2 = apply_transform(x, y, False, False, 90.0, (0.0, 0.0))
    # x2 = x*0 - y*1 = -y -> [-50, 50]
    # y2 = x*1 + y*0 = x -> [100, 200]
    assert np.allclose(x2, [-50, 50])
    assert np.allclose(y2, [100, 200])
    
    # Offset
    x3, y3 = apply_transform(x, y, False, False, 0.0, (10.0, -20.0))
    assert np.allclose(x3, [110, 210])
    assert np.allclose(y3, [30, -70])
    
    # All together: flipX, then rot 90, then offset
    x4, y4 = apply_transform(x, y, True, False, 90.0, (10.0, -20.0))
    # flipX: [-100, -200], [50, -50]
    # rot90: [-50, 50], [-100, -200]
    # offset: [-40, 60], [-120, -220]
    assert np.allclose(x4, [-40, 60])
    assert np.allclose(y4, [-120, -220])

def test_scan_area():
    # Square from 0,0 to 100,100
    quad = [(0,0), (100,0), (100,100), (0,100)]
    assert is_convex_quad(quad) == True
    
    # Non-convex quad (dart shape)
    bad_quad = [(0,0), (100,0), (50,50), (0,100)]
    assert is_convex_quad(bad_quad) == False
    
    x = np.array([50, -10, 50, 100])
    y = np.array([50, 50, 150, 50])
    mask = filter_inside_quad(x, y, quad)
    assert mask.tolist() == [True, False, False, True] # on edge (100,50) is True

def test_background():
    bg = BackgroundModel("L1", learn_scans=2, tolerance_mm=40)
    
    # angles at bins 0 and 1
    angles = np.array([0.1, 0.6]) * math.pi/180.0
    ranges_1 = np.array([1000, 2000])
    ranges_2 = np.array([1010, 1990])
    
    bg.start_learning()
    assert not bg.process_learning_scan(angles, ranges_1)
    assert bg.process_learning_scan(angles, ranges_2)
    
    # median of [1000, 1010] is 1005
    # median of [2000, 1990] is 1995
    assert abs(bg.bg_ranges[0] - 1005) < 1
    assert abs(bg.bg_ranges[1] - 1995) < 1
    
    mask = bg.get_foreground_mask(angles, np.array([1000, 1900]))
    # 1000 is not < (1005 - 40) => False
    # 1900 is < (1995 - 40) => True
    assert mask.tolist() == [False, True]

def test_clustering():
    x = np.array([0, 10, 100, 110, 120, 500])
    y = np.array([0, 0, 0, 0, 0, 0])
    angles = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5])
    
    cx, cy, sz, indices = cluster_points(x, y, angles, cluster_gap_mm=50.0, min_points=2, min_size_mm=5, max_size_mm=50)
    
    # Cluster 1: [0, 10] -> size 10 (valid)
    # Cluster 2: [100, 110, 120] -> size 20 (valid)
    # Cluster 3: [500] -> size 0, dropped due to min_points
    assert len(cx) == 2
    assert cx[0] == 5
    assert cx[1] == 110

def test_tracking():
    tracker = Tracker(confirm_frames=2, lost_frames=3, max_match_dist_uv=0.1)
    
    # Frame 1: One blob
    u1, v1, s1 = np.array([0.5]), np.array([0.5]), np.array([100])
    tracks = tracker.update(u1, v1, s1, 1.0)
    assert len(tracks) == 0 # still "new"
    
    # Frame 2: Blob moves slightly
    u2, v2, s2 = np.array([0.55]), np.array([0.5]), np.array([100])
    tracks = tracker.update(u2, v2, s2, 1.1)
    assert len(tracks) == 1
    assert tracks[0].id == 1
    assert tracks[0].state == "active"
    
    # Frame 3: Missed (lost)
    tracks = tracker.update(np.array([]), np.array([]), np.array([]), 1.2)
    assert len(tracks) == 1
    assert tracks[0].state == "lost"
    
    # Frame 4: Recovered
    tracks = tracker.update(u2, v2, s2, 1.3)
    assert len(tracks) == 1
    assert tracks[0].id == 1
    assert tracks[0].state == "active"
