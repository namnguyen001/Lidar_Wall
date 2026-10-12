# 05 – Mô hình dữ liệu & thiết bị

## Hệ toạ độ
- **Lidar space (mm)**: gốc tại tâm lidar; `x` sang phải, `y` hướng ra phía trước (sau flip/rotation do người dùng chỉnh).
- **Wall UV**: `u` 0→1 trái→phải, `v` 0→1 trên→dưới. `wall.widthPx/heightPx` chỉ dùng để quy đổi "px" khi hiển thị/xuất.
- **Wall physical**: `wall.widthMm/heightMm` dùng cho ngưỡng gộp blob đa lidar.

## Config chính (`data/config.json`) – tóm tắt (schema đầy đủ: `config/config.schema.json`)
```jsonc
{
  "version": 1,
  "wall": { "name":"Main wall", "widthPx":1920, "heightPx":1080, "widthMm":4000, "heightMm":2250 },
  "lidars": [ Lidar ],
  "blob": { /* mặc định toàn cục, xem skill/pipeline.md */ },
  "zones": [ Zone ],
  "output": OutputConfig,
  "ui": { "language":"vi", "topView": { "rangeMm":6000 } }
}
```

### Lidar
```jsonc
{
  "id":"L1", "name":"G4 trái", "model":"ydlidar-g4", "enabled":true,
  "connection": { "kind":"serial", "port":"COM3", "baud":230400 },
  // hoặc { "kind":"tcp", "host":"192.168.0.11", "port":8090 }   // TEA – port đã xác nhận
  // hoặc { "kind":"simulator", "seed":1, "hands":2 }
  "params": { "scanFreqHz":10, "sampleRateKhz":9, "minRangeMm":120, "maxRangeMm":16000, "singleChannel":false },
  "transform": { "flipX":false, "flipY":false, "rotationDeg":0, "offsetMm":[0,0] },
  "scanArea": { "mode":"free|rect", "quadMm":[[x,y],[x,y],[x,y],[x,y]] },   // TL,TR,BR,BL
  "coverageUv": [[0,0],[1,0],[1,1],[0,1]],
  "background": { "toleranceMm":40, "learnScans":60, "learnedAt":null },
  "calibration": { "homography":[[...3],[...3],[...3]] | null, "rmsPx":null, "createdAt":null,
                   "targetsUv":[...], "capturedMm":[...] },
  "overrides": { "blob": { } }
}
```

### Zone
```jsonc
{ "id":"z1","name":"Nút A","enabled":true,"layer":0,"color":"#22D3EE",
  "shape": { "type":"rect","x":0.1,"y":0.1,"w":0.2,"h":0.2 },
  // {"type":"circle","cx":0.5,"cy":0.5,"r":0.05} | {"type":"polygon","points":[[u,v],...]}
  "trigger":"enter|exit|hold|touch", "dwellMs":0, "repeatMs":0, "minBlobs":1, "cooldownMs":0,
  "hysteresisUv":0.005, "exclusiveGroup":null,
  "output": { "oscAddress":null, "tag":null } }
```

### Blob (runtime)
`{ id:int, u, v, sizeMm, vu, vv, state:"active|lost", sources:[lidarId], ageFrames }`

### Preset
`{ id, name, createdAt, includeCalibration:bool, config:{blob,lidars[transform,scanArea,background,overrides],zones,output} }`

## Thiết bị YDLIDAR
| | TEA | G4 |
|---|---|---|
| Kiểu | ToF, Ethernet | Triangulation, Serial/USB |
| Kết nối của bạn | `192.168.0.11` | `COM3`, 230400 |
| Port TCP | `8090` (đã xác nhận) | – |
| Giao thức | Socket RAW (YDLidar Protocol) | PySerial RAW (YDLidar Protocol) |
| Tần số quét | ~10 Hz | ~10 Hz, sample rate ~9 kHz (xác nhận) |

**Việc bắt buộc trước khi code driver chính (prompt 02):** Đã hoàn thành. Chúng ta chọn sử dụng **Driver Python thuần** (RAW byte parser qua socket và pyserial) vì SDK `.pyd` khó setup trên Windows và giao thức chuẩn của YDLidar khá đơn giản (`AA 55`). Tránh được nỗi đau build C++ SDK.
