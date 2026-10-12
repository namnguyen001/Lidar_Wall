from app.drivers.ydlidar_sdk import YdlidarSdkDriver
from app.models.config import ConnectionSerial


def test_decode_packet():
    # Construct a dummy YDLidar packet
    # packet_type = 0x00, sample_count = 2
    # raw_start = 0 (0 degrees), raw_end = 64*2 = 128 (2 degrees)
    # distance = 400 (100 mm)
    
    packet = bytearray(14)
    packet[0] = 0xAA
    packet[1] = 0x55
    packet[2] = 0x00 # type
    packet[3] = 2    # count
    
    # start angle (LSA = 0)
    packet[4] = 0
    packet[5] = 0
    # end angle (FSA = 128 = 2.0 degrees)
    packet[6] = 128
    packet[7] = 0
    
    # distance 1 = 100mm -> 400 -> 0x0190
    packet[10] = 0x90
    packet[11] = 0x01
    
    # distance 2 = 200mm -> 800 -> 0x0320
    packet[12] = 0x20
    packet[13] = 0x03
    
    cfg = ConnectionSerial(kind="serial", port="COM1", baud=115200)
    driver = YdlidarSdkDriver("test1", cfg)
    
    pts = driver._decode_packet(bytes(packet))
    assert len(pts) == 2
    
    # Angle 1 is 0.0 + correction, Angle 2 is 2.0 + correction
    # We just ensure they are floats and ranges are 100 and 200
    assert abs(pts[0][1] - 100.0) < 0.1
    assert abs(pts[1][1] - 200.0) < 0.1
    
def test_driver_lifecycle():
    cfg = ConnectionSerial(kind="serial", port="COM1", baud=115200)
    driver = YdlidarSdkDriver("test2", cfg)
    
    assert driver.get_status().state == "disconnected"
    
    driver.start()
    # It should immediately go into connecting or error (since COM1 doesn't exist)
    import time
    time.sleep(0.1)
    st = driver.get_status()
    assert st.state in ("connecting", "error")
    
    driver.stop()
    assert driver.get_status().state == "disconnected"
