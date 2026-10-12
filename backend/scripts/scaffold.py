import os

# Define the structure and content for backend files
files = {
    "app/__init__.py": "",
    "app/main.py": """
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import api_router
from app.services.lidar_manager import LidarManager
from app.storage.config_store import ConfigStore
from app.services.ws_hub import WsHub

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup state
    app.state.config_store = ConfigStore()
    app.state.config_store.load()
    app.state.ws_hub = WsHub()
    app.state.lidar_manager = LidarManager(app.state.config_store, app.state.ws_hub)
    
    await app.state.lidar_manager.start_all()
    
    yield
    
    # Teardown
    await app.state.lidar_manager.stop_all()

app = FastAPI(title="Lidar Interactive Wall", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "uptimeS": 0}
""",
    "app/api/__init__.py": """
from fastapi import APIRouter
from app.api.endpoints import config, lidars, ws

api_router = APIRouter()
api_router.include_router(config.router, tags=["config"])
api_router.include_router(lidars.router, tags=["lidars"])
api_router.include_router(ws.router, tags=["ws"])
""",
    "app/api/endpoints/__init__.py": "",
    "app/api/endpoints/config.py": """
from fastapi import APIRouter, Request
from app.models.config import LidarWallConfig

router = APIRouter(prefix="/config")

@router.get("", response_model=LidarWallConfig)
async def get_config(request: Request):
    return request.app.state.config_store.get_config()

@router.put("", response_model=LidarWallConfig)
async def update_config(config: LidarWallConfig, request: Request):
    request.app.state.config_store.update_config(config)
    return config
""",
    "app/api/endpoints/lidars.py": """
from fastapi import APIRouter, Request, HTTPException
from typing import List, Dict, Any

router = APIRouter(prefix="/lidars")

@router.get("")
async def get_lidars(request: Request):
    manager = request.app.state.lidar_manager
    config = request.app.state.config_store.get_config()
    res = []
    for lidar_conf in config.lidars:
        status = manager.get_status(lidar_conf.id)
        res.append({"config": lidar_conf.model_dump(), "status": status})
    return res

@router.post("/{lidar_id}/connect")
async def connect_lidar(lidar_id: str, request: Request):
    manager = request.app.state.lidar_manager
    if not await manager.start_lidar(lidar_id):
        raise HTTPException(status_code=404, detail="Lidar not found")
    return {"status": manager.get_status(lidar_id)}

@router.post("/{lidar_id}/disconnect")
async def disconnect_lidar(lidar_id: str, request: Request):
    manager = request.app.state.lidar_manager
    if not await manager.stop_lidar(lidar_id):
        raise HTTPException(status_code=404, detail="Lidar not found")
    return {"status": manager.get_status(lidar_id)}
""",
    "app/api/endpoints/ws.py": """
from fastapi import APIRouter, WebSocket, Request

router = APIRouter()

@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket, request: Request):
    ws_hub = request.app.state.ws_hub
    await ws_hub.connect_events(websocket)

@router.websocket("/ws/points")
async def ws_points(websocket: WebSocket, request: Request):
    ws_hub = request.app.state.ws_hub
    await ws_hub.connect_points(websocket)
""",
    "app/models/__init__.py": "",
    "app/models/config.py": """
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union, Tuple

Point2 = Tuple[float, float]
Quad = Tuple[Point2, Point2, Point2, Point2]

class WallConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = "Main wall"
    widthPx: int = Field(ge=1)
    heightPx: int = Field(ge=1)
    widthMm: float = Field(gt=0)
    heightMm: float = Field(gt=0)

class ConnectionSerial(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field("serial", pattern="^serial$")
    port: str
    baud: int

class ConnectionTcp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field("tcp", pattern="^tcp$")
    host: str
    port: int = Field(ge=1, le=65535)

class ConnectionSimulator(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field("simulator", pattern="^simulator$")
    seed: Optional[int] = None
    hands: int = Field(default=1, ge=0, le=3)

Connection = Union[ConnectionSerial, ConnectionTcp, ConnectionSimulator]

class Transform(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flipX: bool = False
    flipY: bool = False
    rotationDeg: float = 0.0
    offsetMm: Point2 = (0.0, 0.0)

class ScanArea(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = Field(pattern="^(free|rect)$")
    quadMm: Quad

class BlobConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clusterGapMm: float = Field(default=80, ge=5)
    minPoints: int = Field(default=2, ge=1)
    minSizeMm: float = Field(default=30, ge=0)
    maxSizeMm: float = Field(default=300, ge=1)
    confirmFrames: int = Field(default=2, ge=1)
    lostFrames: int = Field(default=3, ge=0)
    maxMatchDistUv: float = Field(default=0.08, ge=0.001, le=1)
    smoothing: float = Field(default=0.4, ge=0, le=1)
    mergeRadiusMm: float = Field(default=60, ge=0)

class BackgroundConfig(BaseModel):
    toleranceMm: float = 40.0
    learnScans: int = 60
    learnedAt: Optional[int] = None

class CalibrationConfig(BaseModel):
    homography: Optional[List[List[float]]] = None
    rmsPx: Optional[float] = None
    createdAt: Optional[int] = None
    targetsUv: List[Point2] = []
    capturedMm: List[List[Point2]] = []

class LidarConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern="^[A-Za-z0-9_-]{1,32}$")
    name: str
    model: str = Field(pattern="^(ydlidar-tea|ydlidar-g4|simulator)$")
    enabled: bool = True
    connection: Connection
    params: dict = {}
    transform: Transform
    scanArea: ScanArea
    coverageUv: Quad
    background: BackgroundConfig = Field(default_factory=BackgroundConfig)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    overrides: dict = {}

class ShapeRect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field("rect", pattern="^rect$")
    x: float
    y: float
    w: float
    h: float

class ShapeCircle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field("circle", pattern="^circle$")
    cx: float
    cy: float
    r: float

class ShapePolygon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field("polygon", pattern="^polygon$")
    points: List[Point2] = Field(min_length=3)

Shape = Union[ShapeRect, ShapeCircle, ShapePolygon]

class ZoneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    enabled: bool = True
    layer: int = 0
    color: str = "#22D3EE"
    shape: Shape
    trigger: str = Field(pattern="^(enter|exit|hold|touch)$")
    dwellMs: int = Field(default=0, ge=0)
    repeatMs: int = Field(default=0, ge=0)
    minBlobs: int = Field(default=1, ge=1)
    cooldownMs: int = Field(default=0, ge=0)
    hysteresisUv: float = Field(default=0.005, ge=0)
    exclusiveGroup: Optional[str] = None
    output: dict = {}

class OscOutput(BaseModel):
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 9000
    rateHz: int = 60

class TuioOutput(BaseModel):
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 3333
    rateHz: int = 60

class WsOutput(BaseModel):
    enabled: bool = False
    port: int = 9100

class CoordinateOutput(BaseModel):
    space: str = "uv"
    wallWidthPx: int = 1920
    wallHeightPx: int = 1080
    flipY: bool = False

class OutputConfig(BaseModel):
    osc: OscOutput = Field(default_factory=OscOutput)
    tuio: TuioOutput = Field(default_factory=TuioOutput)
    ws: WsOutput = Field(default_factory=WsOutput)
    coordinate: CoordinateOutput = Field(default_factory=CoordinateOutput)

class UiConfig(BaseModel):
    language: str = "vi"
    topView: dict = {"rangeMm": 6000}

class LidarWallConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(1, ge=1, le=1)
    wall: WallConfig
    lidars: List[LidarConfig]
    blob: BlobConfig
    zones: List[ZoneConfig]
    output: OutputConfig
    ui: UiConfig = Field(default_factory=UiConfig)
""",
    "app/storage/__init__.py": "",
    "app/storage/config_store.py": """
import json
import os
import shutil
import time
from pathlib import Path
from app.models.config import LidarWallConfig

class ConfigStore:
    def __init__(self, data_dir: str = "../data", config_file: str = "config.json"):
        self.data_dir = Path(data_dir)
        self.config_path = self.data_dir / config_file
        self.config: LidarWallConfig | None = None

    def load(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            default_cfg = Path("../config/default.config.json")
            if default_cfg.exists():
                shutil.copy(default_cfg, self.config_path)
            else:
                raise FileNotFoundError("Default config not found")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.config = LidarWallConfig(**data)

    def get_config(self) -> LidarWallConfig:
        if self.config is None:
            self.load()
        return self.config

    def update_config(self, new_config: LidarWallConfig):
        # debounce logic would go here in a real app or handled at API layer
        
        backup_path = self.config_path.with_suffix('.json.bak')
        tmp_path = self.config_path.with_suffix('.tmp')
        
        if self.config_path.exists():
            shutil.copy(self.config_path, backup_path)
            
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_config.model_dump_json(indent=2))
            
        os.replace(tmp_path, self.config_path)
        self.config = new_config
""",
    "app/drivers/__init__.py": "",
    "app/drivers/base.py": """
from typing import Protocol, List, Tuple
from dataclasses import dataclass
import numpy as np

@dataclass
class ScanFrame:
    points: np.ndarray  # shape (N, 2), float32, x y in mm
    timestamp: float

@dataclass
class DriverStatus:
    state: str = "disconnected" # "disconnected", "connecting", "connected", "error"
    fps: float = 0.0
    scan_count: int = 0
    last_error: str | None = None

class LidarDriver(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def get_status(self) -> DriverStatus: ...
    def get_latest_frame(self) -> ScanFrame | None: ...
""",
    "app/drivers/simulator.py": """
import threading
import time
import numpy as np
import math
from app.drivers.base import LidarDriver, DriverStatus, ScanFrame

class SimulatorDriver(LidarDriver):
    def __init__(self, seed: int = 1, hands: int = 1):
        self.seed = seed
        self.hands = min(max(hands, 0), 3)
        self.status = DriverStatus()
        self._latest_frame = None
        self._stop_event = threading.Event()
        self._thread = None
        np.random.seed(seed)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.status.state = "connecting"
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self.status.state = "disconnected"

    def get_status(self) -> DriverStatus:
        return self.status

    def get_latest_frame(self) -> ScanFrame | None:
        return self._latest_frame

    def _run(self):
        time.sleep(0.5)  # simulate connection delay
        self.status.state = "connected"
        last_time = time.perf_counter()
        
        while not self._stop_event.is_set():
            now = time.perf_counter()
            dt = now - last_time
            if dt >= 0.1:  # 10 Hz
                last_time = now
                self._generate_frame(now)
                self.status.scan_count += 1
                self.status.fps = 1.0 / dt
            else:
                time.sleep(0.01)

    def _generate_frame(self, t: float):
        # Wall at y = 1000, from x = -1000 to x = 1000
        x_wall = np.linspace(-1000, 1000, 400)
        y_wall = np.full_like(x_wall, 1000.0)
        
        points = np.column_stack((x_wall, y_wall))
        
        # Add hands
        for i in range(self.hands):
            hx = math.sin(t + i*2) * 500
            hy = 950 + math.cos(t * 2 + i) * 30
            
            # hand shape
            ang = np.linspace(0, np.pi, 20)
            hx_pts = hx + np.cos(ang) * 40
            hy_pts = hy + np.sin(ang) * 40
            hand_pts = np.column_stack((hx_pts, hy_pts))
            points = np.vstack((points, hand_pts))
            
        # Add noise
        noise = np.random.normal(0, 5, points.shape)
        points += noise
        
        self._latest_frame = ScanFrame(points=points.astype(np.float32), timestamp=t)
""",
    "app/services/__init__.py": "",
    "app/services/lidar_manager.py": """
import os
import asyncio
from typing import Dict, Any
from app.models.config import LidarConfig
from app.drivers.base import LidarDriver, DriverStatus
from app.drivers.simulator import SimulatorDriver
from app.storage.config_store import ConfigStore
from app.services.ws_hub import WsHub

class LidarManager:
    def __init__(self, config_store: ConfigStore, ws_hub: WsHub):
        self.config_store = config_store
        self.ws_hub = ws_hub
        self.drivers: Dict[str, LidarDriver] = {}
        self.force_sim = os.environ.get("LIDAR_FORCE_SIM") == "1"
        self._loop = None

    async def start_all(self):
        self._loop = asyncio.get_running_loop()
        config = self.config_store.get_config()
        for lidar_conf in config.lidars:
            if lidar_conf.enabled:
                await self.start_lidar(lidar_conf.id)
                
        # Start a loop to send lidar statuses
        self._status_task = asyncio.create_task(self._broadcast_status())
        # Start a loop to send raw points (binary)
        self._points_task = asyncio.create_task(self._broadcast_points())

    async def stop_all(self):
        if hasattr(self, '_status_task'):
            self._status_task.cancel()
        if hasattr(self, '_points_task'):
            self._points_task.cancel()
            
        for lidar_id in list(self.drivers.keys()):
            await self.stop_lidar(lidar_id)

    async def start_lidar(self, lidar_id: str) -> bool:
        config = self.config_store.get_config()
        lidar_conf = next((l for l in config.lidars if l.id == lidar_id), None)
        if not lidar_conf:
            return False

        if lidar_id in self.drivers:
            self.drivers[lidar_id].stop()
            
        driver = self._create_driver(lidar_conf)
        self.drivers[lidar_id] = driver
        driver.start()
        return True

    async def stop_lidar(self, lidar_id: str) -> bool:
        if lidar_id in self.drivers:
            self.drivers[lidar_id].stop()
            del self.drivers[lidar_id]
            return True
        return False

    def get_status(self, lidar_id: str) -> dict:
        if lidar_id in self.drivers:
            st = self.drivers[lidar_id].get_status()
            return {"state": st.state, "fps": st.fps, "scanCount": st.scan_count, "lastError": st.last_error}
        return {"state": "disconnected", "fps": 0, "scanCount": 0}

    def _create_driver(self, conf: LidarConfig) -> LidarDriver:
        if self.force_sim or conf.connection.kind == "simulator":
            hands = 1
            if getattr(conf.connection, 'hands', None) is not None:
                hands = conf.connection.hands
            return SimulatorDriver(hands=hands)
        # For now, fallback to simulator if others are not implemented
        return SimulatorDriver()

    async def _broadcast_status(self):
        while True:
            await asyncio.sleep(1.0)
            for lidar_id, driver in self.drivers.items():
                st = driver.get_status()
                msg = {
                    "v": 1,
                    "type": "lidarStatus",
                    "ts": int(asyncio.get_event_loop().time() * 1000),
                    "data": {
                        "id": lidar_id,
                        "state": st.state,
                        "fps": st.fps,
                        "scanCount": st.scan_count,
                        "lastError": st.last_error
                    }
                }
                await self.ws_hub.broadcast_events(msg)
                
    async def _broadcast_points(self):
        import struct
        while True:
            await asyncio.sleep(1.0 / 15.0) # approx 15 Hz max
            for idx, lidar_conf in enumerate(self.config_store.get_config().lidars):
                driver = self.drivers.get(lidar_conf.id)
                if not driver: continue
                frame = driver.get_latest_frame()
                if not frame or frame.points is None: continue
                
                # Format: uint8 version(1) | uint8 res | uint16 lidarIdx | uint32 seq | uint32 ptCount | float32 ts
                # Followed by ptCount x 2 x float32 (x,y) and uint8 flags
                pts = frame.points
                count = len(pts)
                header = struct.pack("<BBHII f", 1, 0, idx, getattr(driver.status, 'scan_count', 0), count, frame.timestamp)
                
                # points payload
                points_bytes = pts.tobytes() # float32 x, y
                # flags payload
                flags = b'\\x00' * count
                
                binary_msg = header + points_bytes + flags
                await self.ws_hub.broadcast_points(binary_msg)
""",
    "app/services/ws_hub.py": """
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class WsHub:
    def __init__(self):
        self.events_clients: List[WebSocket] = []
        self.points_clients: List[WebSocket] = []

    async def connect_events(self, websocket: WebSocket):
        await websocket.accept()
        self.events_clients.append(websocket)
        # Send hello
        hello_msg = {
            "v": 1,
            "type": "hello",
            "ts": int(asyncio.get_event_loop().time() * 1000),
            "data": {"serverVersion": "1.0.0", "config": {}}
        }
        await websocket.send_text(json.dumps(hello_msg))
        try:
            while True:
                data = await websocket.receive_text()
                # handle subscribe etc later
        except WebSocketDisconnect:
            self.events_clients.remove(websocket)

    async def connect_points(self, websocket: WebSocket):
        await websocket.accept()
        self.points_clients.append(websocket)
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            self.points_clients.remove(websocket)

    async def broadcast_events(self, message: dict):
        if not self.events_clients: return
        msg_str = json.dumps(message)
        for client in self.events_clients:
            try:
                await client.send_text(msg_str)
            except:
                pass

    async def broadcast_points(self, message: bytes):
        if not self.points_clients: return
        for client in self.points_clients:
            try:
                await client.send_bytes(message)
            except:
                pass
""",
    "tests/test_config.py": """
from app.storage.config_store import ConfigStore
import pytest
import os
import shutil

def test_config_store(tmp_path):
    # Setup
    data_dir = tmp_path / "data"
    
    # We must ensure default config exists at config/default.config.json relative to cwd
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(tmp_path / "config", exist_ok=True)
    shutil.copy("d:/Lidar/Code/lidar-wall-kit/config/default.config.json", tmp_path / "config" / "default.config.json")
    
    cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        store = ConfigStore(data_dir="data")
        store.load()
        cfg = store.get_config()
        assert cfg.version == 1
        assert len(cfg.lidars) == 2
        
        cfg.wall.name = "Test Wall"
        store.update_config(cfg)
        
        assert os.path.exists("data/config.json")
        assert os.path.exists("data/config.json.bak")
    finally:
        os.chdir(cwd)
""",
    "tests/test_binary.py": """
import struct
import numpy as np

def test_binary_decode_logic():
    # Simulate BE building the message
    idx = 1
    seq = 100
    count = 2
    ts = 123.45
    pts = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
    
    header = struct.pack("<BBHII f", 1, 0, idx, seq, count, ts)
    points_bytes = pts.tobytes()
    flags = b'\\x01\\x00'
    
    msg = header + points_bytes + flags
    
    # Simulate FE parsing
    assert len(msg) == 16 + 2 * 2 * 4 + 2
    v, res, parsed_idx, parsed_seq, parsed_count, parsed_ts = struct.unpack("<BBHII f", msg[:16])
    assert v == 1
    assert parsed_idx == 1
    assert parsed_count == 2
    
    pts_unpacked = np.frombuffer(msg[16:16+16], dtype=np.float32).reshape(-1, 2)
    assert pts_unpacked[0][0] == 10.0
    assert pts_unpacked[1][1] == 40.0
    
    flags_unpacked = msg[32:]
    assert flags_unpacked[0] == 1
"""
}

for path, content in files.items():
    full_path = os.path.join("d:/Lidar/Code/lidar-wall-kit/backend", path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\\n")
