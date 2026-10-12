import pytest
from app.core.zones import hit_test_rect, hit_test_circle, hit_test_polygon, validate_polygon

def test_hit_test_rect_hysteresis():
    rect = {'x': 0.1, 'y': 0.1, 'w': 0.2, 'h': 0.2} # 0.1->0.3
    
    # Inside
    assert hit_test_rect(0.2, 0.2, rect)
    
    # Just outside
    assert not hit_test_rect(0.31, 0.2, rect)
    
    # Inside with hysteresis
    assert hit_test_rect(0.31, 0.2, rect, hysteresis_uv=0.02, currently_inside=True)
    
    # Too far outside with hysteresis
    assert not hit_test_rect(0.33, 0.2, rect, hysteresis_uv=0.02, currently_inside=True)

def test_hit_test_polygon_hysteresis():
    poly = {'points': [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]}
    
    assert hit_test_polygon(0.2, 0.2, poly)
    assert not hit_test_polygon(0.35, 0.2, poly)
    
    # Within hysteresis
    assert hit_test_polygon(0.32, 0.2, poly, hysteresis_uv=0.03, currently_inside=True)

def test_validate_polygon():
    # Square
    assert validate_polygon([[0,0], [1,0], [1,1], [0,1]])
    
    # Self-intersecting bow-tie
    assert not validate_polygon([[0,0], [1,1], [1,0], [0,1]])
