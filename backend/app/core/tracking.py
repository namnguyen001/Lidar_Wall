import numpy as np
from pydantic import BaseModel

from app.core.smoothing import OneEuroFilter


class TrackedBlob(BaseModel):
    id: int
    u: float
    v: float
    size_mm: float
    vu: float = 0.0
    vv: float = 0.0
    state: str = "new" # new -> active -> lost
    sources: list[str] = []
    age_frames: int = 0
    lost_frames: int = 0

class Tracker:
    def __init__(self, confirm_frames: int = 2, lost_frames: int = 3, max_match_dist_uv: float = 0.08, smoothing: float = 0.4):
        self.confirm_frames = confirm_frames
        self.max_lost_frames = lost_frames
        self.max_match_dist_uv = max_match_dist_uv
        
        # Maps smoothing 0..1 to OneEuroFilter parameters
        self.smoothing = smoothing
        self.beta = 0.005 + (1.0 - smoothing) * 0.1 # higher smoothing = lower beta
        self.min_cutoff = 0.5 + (1.0 - smoothing) * 2.0
        
        self.next_id = 1
        self.tracks: dict[int, TrackedBlob] = {}
        self.filters: dict[int, OneEuroFilter] = {}
        
    def update(self, detections_u: np.ndarray, detections_v: np.ndarray, detections_size: np.ndarray, timestamp: float) -> list[TrackedBlob]:
        """
        Updates tracks with new detections in UV space.
        """
        active_ids = list(self.tracks.keys())
        
        if len(active_ids) == 0:
            # All are new
            for i in range(len(detections_u)):
                self._create_track(detections_u[i], detections_v[i], detections_size[i], timestamp)
        elif len(detections_u) == 0:
            # All are lost
            for track_id in active_ids:
                self._mark_lost(track_id)
        else:
            # Cost matrix (euclidean distance)
            track_pts = np.array([[self.tracks[tid].u, self.tracks[tid].v] for tid in active_ids])
            det_pts = np.column_stack((detections_u, detections_v))
            
            # shape: (num_tracks, num_detections)
            diff = track_pts[:, np.newaxis, :] - det_pts[np.newaxis, :, :]
            cost_matrix = np.sqrt(np.sum(diff**2, axis=2))
            
            assigned_tracks = set()
            assigned_dets = set()
            
            # Greedy assignment
            for _ in range(min(len(active_ids), len(detections_u))):
                if np.all(cost_matrix == np.inf):
                    break
                # Find min cost
                r, c = np.unravel_index(np.argmin(cost_matrix), cost_matrix.shape)
                r_idx, c_idx = int(r), int(c)
                dist = cost_matrix[r_idx, c_idx]
                if dist > self.max_match_dist_uv:
                    break
                    
                track_id = active_ids[r_idx]
                self._update_track(track_id, detections_u[c_idx], detections_v[c_idx], detections_size[c_idx], timestamp)
                assigned_tracks.add(track_id)
                assigned_dets.add(c_idx)
                
                # Mask out row and col
                cost_matrix[r_idx, :] = np.inf
                cost_matrix[:, c_idx] = np.inf
                    
            # Handle unassigned tracks
            for track_id in active_ids:
                if track_id not in assigned_tracks:
                    self._mark_lost(track_id)
                    
            # Handle unassigned detections
            for det_idx in range(len(detections_u)):
                if det_idx not in assigned_dets:
                    self._create_track(detections_u[det_idx], detections_v[det_idx], detections_size[det_idx], timestamp)
                    
        # Cleanup and age up
        final_tracks = []
        for track_id in list(self.tracks.keys()):
            track = self.tracks[track_id]
            if track.state == "lost":
                track.lost_frames += 1
                if track.lost_frames > self.max_lost_frames:
                    del self.tracks[track_id]
                    del self.filters[track_id]
                    continue
                # Predict position for lost track (using velocity)
                # We'll just let it coast or stay still. We stay still for simplicity.
                track.u += track.vu * 0.033 # assume ~30fps if coasting
                track.v += track.vv * 0.033
            else:
                track.age_frames += 1
                if track.age_frames >= self.confirm_frames:
                    track.state = "active"
                    
            if track.state == "active" or track.state == "lost":
                final_tracks.append(track)
                
        return final_tracks
        
    def _create_track(self, u: float, v: float, size: float, t: float):
        track_id = self.next_id
        self.next_id += 1
        
        self.tracks[track_id] = TrackedBlob(
            id=track_id, u=u, v=v, size_mm=size, state="new"
        )
        self.filters[track_id] = OneEuroFilter(t, (u, v), self.min_cutoff, self.beta)
        
    def _update_track(self, track_id: int, u: float, v: float, size: float, t: float):
        track = self.tracks[track_id]
        filt = self.filters[track_id]
        
        # Smooth
        smoothed = filt(t, (u, v))
        
        # Calculate velocity
        dt = t - filt.t_prev if filt.t_prev != t else 0.033
        if dt > 0:
            track.vu = (smoothed[0] - track.u) / dt
            track.vv = (smoothed[1] - track.v) / dt
            
        track.u, track.v = smoothed
        # Smoothing size could also be good, but we just EMA it
        track.size_mm = track.size_mm * 0.5 + size * 0.5
        
        track.state = "new" if track.age_frames < self.confirm_frames else "active"
        track.lost_frames = 0
        
    def _mark_lost(self, track_id: int):
        self.tracks[track_id].state = "lost"
