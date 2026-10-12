import socket
import time


def probe_sdk():
    print("--- 1. Probing YDLidar SDK ---")
    try:
        import ydlidar
        print("[OK] Successfully imported ydlidar.")
        print(f"dir(ydlidar): {dir(ydlidar)}")
        return ydlidar
    except ImportError:
        print("[FAIL] Could not import ydlidar. The SDK binding is not installed or failed to load.")
        return None
    except Exception as e:
        print(f"[FAIL] Error loading ydlidar: {e}")
        return None

def probe_tcp(host, ports=[8000, 8090, 80, 23, 2112, 10940]):
    print(f"\n--- 2. Probing TEA TCP Ports at {host} ---")
    open_ports = []
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect((host, port))
                open_ports.append(port)
                print(f"[OK] Port {port} is OPEN.")
        except (TimeoutError, ConnectionRefusedError, OSError):
            print(f"[-] Port {port} is closed/timeout.")
    return open_ports

def probe_g4_sdk(ydlidar, port="COM3", baud=230400):
    print(f"\n--- 3. Probing G4 (Serial) via SDK on {port} ---")
    ydlidar.os_init()
    laser = ydlidar.CYdLidar()
    laser.setlidaropt(ydlidar.LidarPropSerialPort, port)
    laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, baud)
    laser.setlidaropt(ydlidar.LidarPropLidarType, ydlidar.TYPE_TRIANGLE)
    laser.setlidaropt(ydlidar.LidarPropDeviceType, ydlidar.YDLIDAR_TYPE_SERIAL)
    laser.setlidaropt(ydlidar.LidarPropScanFrequency, 10.0)
    laser.setlidaropt(ydlidar.LidarPropSampleRate, 9)
    laser.setlidaropt(ydlidar.LidarPropSingleChannel, False)
    laser.setlidaropt(ydlidar.LidarPropMaxRange, 16.0)
    laser.setlidaropt(ydlidar.LidarPropMinRange, 0.12)
    laser.setlidaropt(ydlidar.LidarPropMaxAngle, 180.0)
    laser.setlidaropt(ydlidar.LidarPropMinAngle, -180.0)

    if not laser.initialize():
        print("[FAIL] G4 Failed to initialize.")
        return
    if not laser.turnOn():
        print("[FAIL] G4 Failed to turn on.")
        return
    
    print("[OK] G4 initialized and turned on. Reading 10 scans...")
    scan = ydlidar.LaserScan()
    start_time = time.time()
    valid_scans = 0
    for i in range(10):
        if laser.doProcessSimple(scan):
            pts = list(scan.points)
            valid_scans += 1
            if pts:
                angles = [p.angle for p in pts if p.range > 0]
                ranges = [p.range for p in pts if p.range > 0]
                if ranges:
                    print(f"  Scan {i+1}: {len(pts)} points, Valid: {len(ranges)}, Angle(min/max): {min(angles):.2f}/{max(angles):.2f} rad, Range(min/max): {min(ranges):.2f}/{max(ranges):.2f} m")
                else:
                    print(f"  Scan {i+1}: {len(pts)} points, 0 valid ranges.")
        else:
            print(f"  Scan {i+1}: Failed to read.")
    end_time = time.time()
    print(f"Actual FPS: {valid_scans / (end_time - start_time):.2f} Hz")
    laser.turnOff()
    laser.disconnecting()

def probe_tea_sdk(ydlidar, host, port):
    print(f"\n--- 4. Probing TEA (TCP) via SDK on {host}:{port} ---")
    ydlidar.os_init()
    laser = ydlidar.CYdLidar()
    laser.setlidaropt(ydlidar.LidarPropSerialPort, host)
    # The TCP port is often passed via SerialBaudrate in the SDK
    laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, port)
    laser.setlidaropt(ydlidar.LidarPropLidarType, getattr(ydlidar, 'TYPE_TOF', 2))
    laser.setlidaropt(ydlidar.LidarPropDeviceType, getattr(ydlidar, 'YDLIDAR_TYPE_TCP', 1))
    
    # TEA common configs (may need adjusting)
    laser.setlidaropt(ydlidar.LidarPropScanFrequency, 10.0)
    laser.setlidaropt(ydlidar.LidarPropSampleRate, 20)
    laser.setlidaropt(ydlidar.LidarPropSingleChannel, False)
    
    if not laser.initialize():
        print("[FAIL] TEA Failed to initialize.")
        return
    if not laser.turnOn():
        print("[FAIL] TEA Failed to turn on.")
        return
        
    print("[OK] TEA initialized and turned on. Reading 10 scans...")
    scan = ydlidar.LaserScan()
    start_time = time.time()
    valid_scans = 0
    for i in range(10):
        if laser.doProcessSimple(scan):
            pts = list(scan.points)
            valid_scans += 1
            if pts:
                angles = [p.angle for p in pts if p.range > 0]
                ranges = [p.range for p in pts if p.range > 0]
                if ranges:
                    print(f"  Scan {i+1}: {len(pts)} points, Valid: {len(ranges)}, Angle(min/max): {min(angles):.2f}/{max(angles):.2f} rad, Range(min/max): {min(ranges):.2f}/{max(ranges):.2f} m")
                else:
                    print(f"  Scan {i+1}: {len(pts)} points, 0 valid ranges.")
        else:
            print(f"  Scan {i+1}: Failed to read.")
    end_time = time.time()
    print(f"Actual FPS: {valid_scans / (end_time - start_time):.2f} Hz")
    laser.turnOff()
    laser.disconnecting()

if __name__ == '__main__':
    ydlidar_module = probe_sdk()
    open_ports = probe_tcp("192.168.0.11")
    
    if ydlidar_module:
        probe_g4_sdk(ydlidar_module, port="COM3", baud=230400)
        if open_ports:
            # Probe with the first open port found
            probe_tea_sdk(ydlidar_module, "192.168.0.11", open_ports[0])
    
    print("\n--- PROBE COMPLETED ---")
