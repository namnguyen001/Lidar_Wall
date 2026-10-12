import logging
import math
import socket
import threading
import time
from collections import deque

import numpy as np
import serial

from app.drivers.base import DriverStatus, LidarDriver, ScanFrame
from app.models.config import ConnectionSerial, ConnectionTcp

logger = logging.getLogger(__name__)

class YdlidarSdkDriver(LidarDriver):
    def __init__(self, lidar_id: str, cfg: ConnectionSerial | ConnectionTcp):
        self.id = lidar_id
        self.cfg = cfg
        
        self._status = DriverStatus(
            state="disconnected",
            fps=0.0,
            scan_count=0,
            last_error=None
        )
        
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._latest_scan: deque[ScanFrame] = deque(maxlen=1)
        
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name=f"Lidar-{self.id}", daemon=True)
        self._thread.start()
        
    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def get_status(self) -> DriverStatus:
        return self._status
            
    def get_latest_frame(self) -> ScanFrame | None:
        try:
            return self._latest_scan.pop()
        except IndexError:
            return None

    def _run_loop(self):
        backoff = 1.0
        while not self._stop_event.is_set():
            self._status.state = "connecting"
            self._status.last_error = None
            
            try:
                if isinstance(self.cfg, ConnectionSerial):
                    self._read_serial()
                elif isinstance(self.cfg, ConnectionTcp):
                    self._read_tcp()
                backoff = 1.0  # Reset backoff on successful connect/read loop exit
            except Exception as e: # noqa: BLE001
                self._status.state = "error"
                self._status.last_error = str(e)
                logger.error(f"Lidar {self.id} error: {e}")
                
            if not self._stop_event.is_set():
                # Exponential backoff 1 -> 10s
                time.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

        self._status.state = "disconnected"

    def _read_serial(self):
        port = self.cfg.port
        baud = self.cfg.baud
        try:
            with serial.Serial(port=port, baudrate=baud, timeout=0.5) as ser:
                ser.dtr = False
                ser.rts = False
                
                # Send Start Scan command for standard YDLIDAR (G4/X4/etc)
                ser.write(b'\xA5\x60')
                time.sleep(0.1)
                
                self._status.state = "connected"
                self._parse_stream(ser)
                
                # Send Stop Scan command when exiting
                ser.write(b'\xA5\x65')
                ser.flush()
                time.sleep(0.1) # Wait briefly for hardware to process stop
        except serial.SerialException as e:
            if "PermissionError" in str(e) or "Access is denied" in str(e):
                raise RuntimeError(f"COM Port {port} is busy. Is tea_test.exe or another app using it?")
            raise

    def _read_tcp(self):
        host = self.cfg.host
        port = self.cfg.port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2.0)
            sock.connect((host, port))
            
            # Send Start Scan command (often same for TEA if configured for custom start, or ignored if auto)
            sock.sendall(b'\xA5\x60')
            
            sock.settimeout(0.5)
            self._status.state = "connected"
            class SockFile:
                def read(self, size):
                    try:
                        return sock.recv(size)
                    except socket.timeout:
                        return b""
            self._parse_stream(SockFile())
            sock.sendall(b'\xA5\x65')

    def _parse_stream(self, stream):
        buffer = bytearray()
        scan_points = []
        last_scan_time = time.monotonic()
        empty_count = 0
        
        while not self._stop_event.is_set():
            chunk = stream.read(1024)
            if not chunk:
                empty_count += 1
                if empty_count > 4:
                    raise TimeoutError("No data received from lidar")
                continue
            
            empty_count = 0
            buffer.extend(chunk)
            
            while True:
                idx = buffer.find(b"\xAA\x55")
                if idx < 0:
                    buffer.clear()
                    break
                if idx > 0:
                    del buffer[:idx]
                if len(buffer) < 10:
                    break
                    
                sample_count = buffer[3]
                packet_length = 10 + sample_count * 2
                if len(buffer) < packet_length:
                    break
                    
                packet = bytes(buffer[:packet_length])
                del buffer[:packet_length]
                
                packet_type = packet[2]
                if packet_type == 0x00:
                    pts = self._decode_packet(packet)
                    scan_points.extend(pts)
                
                if packet_type & 0x01 == 0x01:
                    if len(scan_points) > 50:
                        self._emit_scan(scan_points, last_scan_time)
                        last_scan_time = time.monotonic()
                    scan_points = []

    def _decode_packet(self, packet: bytes) -> list[tuple[float, float]]:
        sample_count = packet[3]
        if sample_count == 0:
            return []

        raw_start = int.from_bytes(packet[4:6], "little") >> 1
        raw_end = int.from_bytes(packet[6:8], "little") >> 1

        start_angle = raw_start / 64.0
        end_angle = raw_end / 64.0
        diff = end_angle - start_angle
        if diff < 0:
            diff += 360.0

        angle_step = diff / (sample_count - 1) if sample_count > 1 else 0.0
        points = []
        for i in range(sample_count):
            offset = 10 + i * 2
            distance_mm = int.from_bytes(packet[offset:offset+2], "little") / 4.0
            
            if distance_mm <= 0:
                continue

            angle_deg = start_angle + i * angle_step
            try:
                angle_correct = math.degrees(math.atan(21.8 * (155.3 - distance_mm) / (155.3 * distance_mm)))
            except ZeroDivisionError:
                angle_correct = 0.0
                
            true_angle_deg = (angle_deg + angle_correct) % 360.0
            points.append((math.radians(true_angle_deg), distance_mm))
            
        return points

    def _emit_scan(self, scan_points: list[tuple[float, float]], last_time: float):
        self._status.scan_count += 1
        now = time.monotonic()
        fps = 1.0 / (now - last_time) if now > last_time else 0.0
        self._status.fps = self._status.fps * 0.8 + fps * 0.2
        
        arr = []
        for angle_rad, distance_mm in scan_points:
            # x = r * sin(theta), y = r * cos(theta)
            x = distance_mm * math.sin(angle_rad)
            y = distance_mm * math.cos(angle_rad)
            arr.append([x, y])
            
        points_np = np.array(arr, dtype=np.float32) if arr else np.zeros((0, 2), dtype=np.float32)
        
        self._latest_scan.append(ScanFrame(
            points=points_np,
            timestamp=now
        ))
