
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Point2 = tuple[float, float]
Quad = tuple[Point2, Point2, Point2, Point2]

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
    seed: int | None = None
    hands: int = Field(default=1, ge=0, le=3)

Connection = ConnectionSerial | ConnectionTcp | ConnectionSimulator

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
    learnedAt: int | None = None

class CalibrationConfig(BaseModel):
    homography: list[list[float]] | None = None
    rmsPx: float | None = None
    createdAt: int | None = None
    targetsUv: list[Point2] | list[list[float]] = []
    capturedMm: list[Point2] | list[list[float]] = []

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
    points: list[Point2] = Field(min_length=3)

Shape = ShapeRect | ShapeCircle | ShapePolygon

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
    exclusiveGroup: str | None = None
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
    theme: Literal["light", "dark"] = "light"
    wallTheme: Literal["light", "dark"] = "dark"
    topView: dict = {"rangeMm": 6000}

class LidarWallConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(1, ge=1, le=1)
    wall: WallConfig
    lidars: list[LidarConfig]
    blob: BlobConfig
    zones: list[ZoneConfig]
    output: OutputConfig
    ui: UiConfig = Field(default_factory=UiConfig)
