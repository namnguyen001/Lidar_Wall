# YDLIDAR drivers

Hardware in this project
- **TEA** (ToF, Ethernet): IP `192.168.0.11`. TCP port is **not verified** – YDLIDAR TCP models commonly use `8000` in SDK examples; confirm with the datasheet / SDK sample / a port probe.
- **G4** (triangulation, serial): `COM3`, baud `230400`, typically ~9 kHz sample rate, 10 Hz scan, range ≈ 0.12–16 m (verify in datasheet).

## Driver interface (backend/app/drivers/base.py)
```python
class LidarDriver(Protocol):
    id: str
    def start(self) -> None: ...          # spawn thread, connect with backoff
    def stop(self) -> None: ...
    def latest(self) -> ScanFrame | None: ...   # non-blocking, returns newest unseen scan or None
    status: DriverStatus   # state: disconnected|connecting|connected|error, fps, lastError, scanCount
```
`ScanFrame`: `ts: float (monotonic), angles_rad: float32[N], ranges_mm: float32[N], intensity: float32[N] | None`.
Implementations: `YdlidarSdkDriver`, `SimulatorDriver`, (optional fallback) `YdlidarSerialDriver` using pyserial if the SDK binding cannot be built.

## YDLIDAR SDK (Python binding) – reference usage
Names below follow the official YDLidar-SDK Python examples; **verify against the installed build** (print `dir(ydlidar)` in the probe script).
```python
import ydlidar
ydlidar.os_init()
laser = ydlidar.CYdLidar()
# G4 (serial)
laser.setlidaropt(ydlidar.LidarPropSerialPort, "COM3")
laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, 230400)
laser.setlidaropt(ydlidar.LidarPropLidarType, ydlidar.TYPE_TRIANGLE)
laser.setlidaropt(ydlidar.LidarPropDeviceType, ydlidar.YDLIDAR_TYPE_SERIAL)
laser.setlidaropt(ydlidar.LidarPropScanFrequency, 10.0)
laser.setlidaropt(ydlidar.LidarPropSampleRate, 9)
laser.setlidaropt(ydlidar.LidarPropSingleChannel, False)
laser.setlidaropt(ydlidar.LidarPropMaxRange, 16.0)
laser.setlidaropt(ydlidar.LidarPropMinRange, 0.12)
laser.setlidaropt(ydlidar.LidarPropMaxAngle, 180.0)
laser.setlidaropt(ydlidar.LidarPropMinAngle, -180.0)
# TEA (TCP) – ASSUMPTIONS to confirm
# laser.setlidaropt(ydlidar.LidarPropSerialPort, "192.168.0.11")
# laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, 8000)   # SDK reuses this field as TCP port
# laser.setlidaropt(ydlidar.LidarPropLidarType, ydlidar.TYPE_TOF)
# laser.setlidaropt(ydlidar.LidarPropDeviceType, ydlidar.YDLIDAR_TYPE_TCP)
if laser.initialize() and laser.turnOn():
    scan = ydlidar.LaserScan()
    while running:
        if laser.doProcessSimple(scan):
            for p in scan.points:  # p.angle (rad), p.range (m), p.intensity
                ...
laser.turnOff(); laser.disconnecting()
```
Convert: `ranges_mm = range_m * 1000`. Filter `range <= 0`.

## Threading & reconnect
- One daemon thread per driver. Loop: connect → read → on failure set status `error`, sleep with exponential backoff (1,2,4,… max 10 s) → reconnect.
- Hand off scans via a `deque(maxlen=1)` / lock-protected slot: consumer always gets the newest scan, never a queue backlog.
- Orderly shutdown: `stop()` sets event, joins thread (timeout 3 s), calls `turnOff()`/`disconnecting()`.
- COM port busy on Windows (another app, e.g. YDLidar viewer) is the #1 failure → surface a clear error message.

## Network (TEA)
PC NIC must be on `192.168.0.x/24` (e.g. `192.168.0.10`), no gateway needed. Allow the app through Windows Firewall. A simple reachability probe: TCP connect to `ip:port` with 1 s timeout.

## Simulator driver
Generates a 10 Hz scan: a straight wall line at configurable distance + 0–3 moving "hands" (Lissajous or scripted paths) as 40–80 mm clusters in front of the wall, with Gaussian noise σ≈5 mm. Must be deterministic with a seed. Supports `walls`/`handsCount`/`speed` in config. Use it for all tests and demos.
