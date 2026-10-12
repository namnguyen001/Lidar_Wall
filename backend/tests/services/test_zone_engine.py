import pytest
import asyncio
from app.services.zone_engine import ZoneEngine
from app.models.config import ZoneConfig, ShapeRect

class DummyWsHub:
    def __init__(self):
        self.events = []
    async def broadcast_events(self, msg):
        self.events.append(msg)

class DummyConfigStore:
    def __init__(self):
        self.config = type('Config', (), {'zones': [], 'wall': type('Wall', (), {'widthPx': 1920, 'heightPx': 1080})()})()
    def get_config(self):
        return self.config

class DummyBlob:
    def __init__(self, id, u, v):
        self.id = id
        self.u = u
        self.v = v

@pytest.mark.asyncio
async def test_zone_engine_enter_exit_hold():
    cfg_store = DummyConfigStore()
    ws_hub = DummyWsHub()
    
    zone = ZoneConfig(
        id="z1", name="Zone 1", enabled=True,
        shape=ShapeRect(x=0.0, y=0.0, w=0.5, h=0.5),
        trigger="enter", dwellMs=0, minBlobs=1
    )
    cfg_store.config.zones.append(zone)
    
    engine = ZoneEngine(cfg_store, ws_hub)
    
    # Test enter
    blobs = [DummyBlob(1, 0.25, 0.25)]
    await engine.process_blobs(blobs, 1.0)
    await asyncio.sleep(0)
    
    # Expect enter event and zoneState
    assert len(ws_hub.events) == 2
    ev1 = ws_hub.events[0]["data"]
    assert ev1["zoneId"] == "z1" and ev1.get("event") == "enter"
    
    ws_hub.events.clear()
    
    # Test hold
    zone.trigger = "hold"
    zone.dwellMs = 100
    
    await engine.process_blobs(blobs, 1.05) # 50ms (no hold yet)
    await asyncio.sleep(0)
    assert len(ws_hub.events) == 1 # only zoneState
    ws_hub.events.clear()
    
    await engine.process_blobs(blobs, 1.15) # 150ms (hold triggered)
    await asyncio.sleep(0)
    assert len(ws_hub.events) == 2
    assert ws_hub.events[0]["data"]["event"] == "hold"
    ws_hub.events.clear()
    
    # Test exit
    zone.trigger = "exit"
    blobs = [DummyBlob(1, 0.6, 0.6)]
    await engine.process_blobs(blobs, 1.2)
    await asyncio.sleep(0)
    assert len(ws_hub.events) == 2
    assert ws_hub.events[0]["data"]["event"] == "exit"
    assert ws_hub.events[0]["data"]["reason"] == "exit"
    ws_hub.events.clear()

@pytest.mark.asyncio
async def test_zone_engine_lost():
    cfg_store = DummyConfigStore()
    ws_hub = DummyWsHub()
    
    zone = ZoneConfig(
        id="z1", name="Zone 1", enabled=True,
        shape=ShapeRect(x=0.0, y=0.0, w=0.5, h=0.5),
        trigger="exit", dwellMs=0, minBlobs=1
    )
    cfg_store.config.zones.append(zone)
    
    engine = ZoneEngine(cfg_store, ws_hub)
    
    # Enter
    blobs = [DummyBlob(1, 0.25, 0.25)]
    await engine.process_blobs(blobs, 1.0)
    await asyncio.sleep(0)
    ws_hub.events.clear()
    
    # Lost (disappear completely)
    await engine.process_blobs([], 1.1)
    await asyncio.sleep(0)
    
    assert len(ws_hub.events) == 2
    assert ws_hub.events[0]["data"]["event"] == "exit"
    assert ws_hub.events[0]["data"]["reason"] == "lost"
