import time
import asyncio
from typing import Any

from app.core.zones import hit_test_rect, hit_test_circle, hit_test_polygon
from app.services.ws_hub import WsHub
from app.storage.config_store import ConfigStore
from app.models.config import ZoneConfig

class ZoneState:
    def __init__(self):
        self.blobs: dict[int, dict] = {} # blob_id -> { "enter_time": float, "last_hold_time": float, "state": "inside" | "held" }
        
class ZoneEngine:
    def __init__(self, config_store: ConfigStore, ws_hub: WsHub):
        self.config_store = config_store
        self.ws_hub = ws_hub
        self.states: dict[str, ZoneState] = {} # zone_id -> ZoneState
        
    def _hit_test(self, u: float, v: float, zone: ZoneConfig, wall_width_px: int, wall_height_px: int, inside: bool) -> bool:
        shape_dict = zone.shape.model_dump()
        hyst = zone.hysteresisUv
        
        if zone.shape.type == "rect":
            return hit_test_rect(u, v, shape_dict, hyst, inside)
        elif zone.shape.type == "circle":
            return hit_test_circle(u, v, shape_dict, wall_width_px, wall_height_px, hyst, inside)
        elif zone.shape.type == "polygon":
            return hit_test_polygon(u, v, shape_dict, hyst, inside)
            
        return False
        
    async def process_blobs(self, blobs: list[Any], current_time: float):
        cfg = self.config_store.get_config()
        if not cfg.zones:
            return
            
        # 1. Sort zones by layer (descending) for exclusive groups
        sorted_zones = sorted(cfg.zones, key=lambda z: z.layer, reverse=True)
        
        wall_w = cfg.wall.widthPx
        wall_h = cfg.wall.heightPx
        
        # We need to know which exclusive groups have been hit by which blob
        blob_exclusive_hits: dict[int, set[str]] = {b.id: set() for b in blobs}
        
        # Track which blobs are still active globally
        active_blob_ids = {b.id for b in blobs}
        
        events_to_broadcast = []
        
        for zone in sorted_zones:
            if not zone.enabled:
                if zone.id in self.states:
                    self.states[zone.id].blobs.clear()
                continue
                
            if zone.id not in self.states:
                self.states[zone.id] = ZoneState()
                
            z_state = self.states[zone.id]
            current_inside_blob_ids = set()
            
            for b in blobs:
                # Check exclusive
                if zone.exclusiveGroup and zone.exclusiveGroup in blob_exclusive_hits[b.id]:
                    continue # Blob already hit a higher-layer zone in this group
                    
                was_inside = b.id in z_state.blobs
                is_inside = self._hit_test(b.u, b.v, zone, wall_w, wall_h, was_inside)
                
                if is_inside:
                    current_inside_blob_ids.add(b.id)
                    if zone.exclusiveGroup:
                        blob_exclusive_hits[b.id].add(zone.exclusiveGroup)
                        
                    if not was_inside:
                        # Enter
                        z_state.blobs[b.id] = {
                            "enter_time": current_time,
                            "last_hold_time": 0.0,
                            "state": "inside"
                        }
                        
                        if zone.trigger in ["enter", "touch"]:
                            events_to_broadcast.append({
                                "type": "zoneEvent",
                                "data": {
                                    "event": "enter",
                                    "zoneId": zone.id,
                                    "blobId": b.id,
                                    "u": b.u,
                                    "v": b.v,
                                    "ts": int(current_time * 1000)
                                }
                            })
                    else:
                        # Hold logic
                        b_state = z_state.blobs[b.id]
                        dwell = zone.dwellMs / 1000.0
                        repeat = zone.repeatMs / 1000.0
                        
                        if zone.trigger == "hold":
                            time_inside = current_time - b_state["enter_time"]
                            if b_state["state"] == "inside" and time_inside >= dwell:
                                b_state["state"] = "held"
                                b_state["last_hold_time"] = current_time
                                events_to_broadcast.append({
                                    "type": "zoneEvent",
                                    "data": {
                                        "event": "hold",
                                        "zoneId": zone.id,
                                        "blobId": b.id,
                                        "u": b.u,
                                        "v": b.v,
                                        "ts": int(current_time * 1000)
                                    }
                                })
                            elif b_state["state"] == "held" and repeat > 0:
                                time_since_hold = current_time - b_state["last_hold_time"]
                                if time_since_hold >= repeat:
                                    b_state["last_hold_time"] = current_time
                                    events_to_broadcast.append({
                                        "type": "zoneEvent",
                                        "data": {
                                            "event": "hold",
                                            "zoneId": zone.id,
                                            "blobId": b.id,
                                            "u": b.u,
                                            "v": b.v,
                                            "ts": int(current_time * 1000)
                                        }
                                    })
                        elif zone.trigger == "touch":
                            events_to_broadcast.append({
                                "type": "zoneEvent",
                                "data": {
                                    "event": "touch",
                                    "zoneId": zone.id,
                                    "blobId": b.id,
                                    "u": b.u,
                                    "v": b.v,
                                    "ts": int(current_time * 1000)
                                }
                            })
            
            # Check for exits and lost
            exited_blob_ids = []
            for b_id, b_state in list(z_state.blobs.items()):
                if b_id not in current_inside_blob_ids:
                    exited_blob_ids.append(b_id)
                    reason = "lost" if b_id not in active_blob_ids else "exit"
                    
                    if zone.trigger in ["exit", "touch", "enter"]:
                        # Also emit exit for enter/touch to allow UI to know
                        events_to_broadcast.append({
                            "type": "zoneEvent",
                            "data": {
                                "event": "exit",
                                "zoneId": zone.id,
                                "blobId": b_id,
                                "u": 0.0, # We don't have exact u,v here if lost, could cache last
                                "v": 0.0,
                                "ts": int(current_time * 1000),
                                "reason": reason
                            }
                        })
                    del z_state.blobs[b_id]
                    
            # Broadcast zoneState if changed
            # Actually, we should broadcast zoneState periodically or on change
            # Let's just always broadcast zoneState for zones that have blobs or just had an event
            if len(current_inside_blob_ids) > 0 or len(exited_blob_ids) > 0:
                # But wait, minBlobs logic
                if len(current_inside_blob_ids) >= zone.minBlobs:
                    pass # We already emitted events, but should we gate events by minBlobs?
                    # The prompt says: minBlobs - maybe affects whether zone is considered "active"
                
                events_to_broadcast.append({
                    "type": "zoneState",
                    "data": {
                        "zoneId": zone.id,
                        "count": len(current_inside_blob_ids),
                        "blobIds": list(current_inside_blob_ids)
                    }
                })
                
        # Send WS events and Output Manager
        for ev in events_to_broadcast:
            if getattr(self, 'output_manager', None):
                if ev["type"] == "zoneEvent":
                    d = ev["data"]
                    self.output_manager.process_zone_event(
                        event=d["event"], zone_id=d["zoneId"], blob_id=d["blobId"], u=d["u"], v=d["v"], count=len(self.states[d["zoneId"]].blobs)
                    )
                elif ev["type"] == "zoneState":
                    d = ev["data"]
                    self.output_manager.process_zone_event(
                        event="count", zone_id=d["zoneId"], blob_id=0, u=0, v=0, count=d["count"]
                    )
                    
            asyncio.create_task(self.ws_hub.broadcast_events({
                "v": 1,
                "type": ev["type"],
                "ts": int(current_time * 1000),
                "data": ev["data"]
            }))
