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
    flags = b'\x01\x00'
    
    msg = header + points_bytes + flags
    
    # Simulate FE parsing
    assert len(msg) == 16 + 2 * 2 * 4 + 2
    v, _res, parsed_idx, _parsed_seq, parsed_count, _parsed_ts = struct.unpack("<BBHII f", msg[:16])
    assert v == 1
    assert parsed_idx == 1
    assert parsed_count == 2
    
    pts_unpacked = np.frombuffer(msg[16:16+16], dtype=np.float32).reshape(-1, 2)
    assert pts_unpacked[0][0] == 10.0
    assert pts_unpacked[1][1] == 40.0
    
    flags_unpacked = msg[32:]
    assert flags_unpacked[0] == 1
