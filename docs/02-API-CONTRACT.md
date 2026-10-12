# 02 – API Contract (FE ↔ BE)

**Nguồn sự thật.** Đổi message = sửa file này trước, rồi mới sửa code. Base: `http://localhost:8080`. JSON, camelCase.
Đơn vị: lidar = **mm**; tường = **UV 0..1** (gốc trên-trái, y xuống); thời gian `ts` = ms epoch (số) trừ khi ghi khác.

## Lỗi chuẩn
HTTP 4xx/5xx body: `{ "error": { "code": "LIDAR_NOT_FOUND", "message": "...", "details": {...} } }`
Mã: `VALIDATION_ERROR`(422) · `LIDAR_NOT_FOUND`(404) · `ZONE_NOT_FOUND`(404) · `LIDAR_CONNECT_FAILED`(502) · `CALIBRATION_BUSY`(409) · `CALIBRATION_NOT_ACTIVE`(409) · `CALIBRATION_FAILED`(422) · `PRESET_NOT_FOUND`(404) · `INTERNAL`(500).

## REST

### Hệ thống & cấu hình
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/health` | `{status:"ok", version, uptimeS}` |
| GET | `/api/config` | Toàn bộ cấu hình (docs/05) |
| PUT | `/api/config` | Thay toàn bộ (validate) |
| GET | `/api/config/export` | Tải file JSON |
| POST | `/api/config/import` | Upload JSON, validate rồi áp dụng |

### Lidar
| Method | Path | Body → Response |
|---|---|---|
| GET | `/api/lidars` | → `Lidar[]` (config + `status`) |
| POST | `/api/lidars` | `LidarCreate` → `Lidar` (201) |
| PATCH | `/api/lidars/{id}` | `LidarPatch` (flipX, flipY, rotationDeg, offsetMm, enabled, connection, overrides…) → `Lidar` |
| DELETE | `/api/lidars/{id}` | 204 |
| POST | `/api/lidars/{id}/connect` | → `LidarStatus` |
| POST | `/api/lidars/{id}/disconnect` | → `LidarStatus` |
| PUT | `/api/lidars/{id}/scan-area` | `ScanArea` → `ScanArea` |
| POST | `/api/lidars/{id}/background/learn` | `{scans?:number}` → `{state:"learning"}` (tiến độ qua WS) |
| DELETE | `/api/lidars/{id}/calibration` | Xoá hiệu chỉnh |
| GET | `/api/lidars/probe` | `?kind=tcp&host=...&port=...` hoặc `?kind=serial&port=COM3&baud=230400` → `{reachable, detail}` |
| GET | `/api/serial-ports` | → `[{port:"COM3", description}]` |

### Hiệu chỉnh
| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/calibration/start` | `{lidarId, targetsUv?, samplesPerPoint?}` → `CalibrationState` |
| GET | `/api/calibration/state` | → `CalibrationState` |
| POST | `/api/calibration/capture` | Capture ngay điểm hiện tại (phím Space) |
| POST | `/api/calibration/redo` | `{pointIndex}` làm lại 1 điểm |
| POST | `/api/calibration/cancel` | Huỷ (phím Esc) |
| POST | `/api/calibration/commit` | Chấp nhận kết quả REVIEW → lưu |

### Zone
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/zones` | `Zone[]` |
| POST | `/api/zones` | `ZoneCreate` → `Zone` (201) |
| PUT | `/api/zones/{id}` | `Zone` → `Zone` |
| DELETE | `/api/zones/{id}` | 204 |
| POST | `/api/zones/{id}/duplicate` | → `Zone` |
| PUT | `/api/zones` | thay cả danh sách (import) |

### Output & Preset
| Method | Path | Mô tả |
|---|---|---|
| GET/PUT | `/api/output` | `OutputConfig` |
| POST | `/api/output/test` | gửi 1 blob giả để thử |
| GET | `/api/presets` | `PresetMeta[]` |
| POST | `/api/presets` | `{name}` → lưu cấu hình hiện tại (trừ calibration nếu `includeCalibration=false`) |
| POST | `/api/presets/{id}/apply` | áp dụng |
| DELETE | `/api/presets/{id}` | xoá |

## WebSocket `/ws/events` (JSON)
Envelope: `{ "v":1, "type":"...", "ts":1730000000000, "seq":123, "data":{...} }`. `seq` tăng dần theo từng kết nối.
Client có thể gửi: `{type:"subscribe", topics:["blobs","lidarStatus","zones","calibration","bgLearn"]}` (mặc định tất cả).

| type | data |
|---|---|
| `hello` | `{serverVersion, config: ConfigSummary}` ngay khi kết nối |
| `lidarStatus` | `{id, state:"disconnected|connecting|connected|error", fps, scanCount, lastError?}` (khi đổi + mỗi 1 s) |
| `blobs` | `{blobs:[{id, u, v, sizeMm, vu, vv, state:"active|lost", sources:[lidarId], age}]}` ≤ 30 Hz; rỗng cũng gửi 1 lần khi hết blob |
| `rawBlobs` | `{lidarId, blobs:[{x, y, sizeMm}]}` (mm, lidar space – cho top view/calibration) |
| `zoneEvent` | `{event:"enter|hold|exit", zoneId, blobId, u, v, reason?}` |
| `zoneState` | `{zoneId, count, blobIds:[]}` |
| `calibration` | `CalibrationState` (mỗi thay đổi, và ≤ 15 Hz trong CAPTURING/WAIT_HAND) |
| `bgLearn` | `{lidarId, progress:0..1, state:"learning|done|failed"}` |
| `error` | `{code, message, lidarId?}` |

### CalibrationState
```json
{
 "state": "IDLE|WAIT_HAND|CAPTURING|COMPUTE|REVIEW|COMMITTED|CANCELLED|FAILED",
 "lidarId": "L1",
 "pointIndex": 1, "pointCount": 4,
 "targetsUv": [[0.1,0.1],[0.9,0.1],[0.9,0.9],[0.1,0.9]],
 "currentTargetUv": [0.9,0.1],
 "handUv": [0.85,0.14],            // theo ánh xạ tạm; null nếu chưa có blob
 "distancePx": 125,
 "samples": 35, "samplesNeeded": 40,
 "capturedMm": [[...],[...]],
 "result": { "rmsPx": 8.2, "maxPx": 14.1, "wallQuadUv": [[..],[..],[..],[..]], "ok": true },
 "message": "Move hand to orange point"
}
```

## WebSocket `/ws/points` (binary, little-endian)
Header 16 byte: `uint8 version(=1) | uint8 reserved | uint16 lidarIndex | uint32 seq | uint32 pointCount | float32 timestampS`
Theo sau `pointCount × 2 × float32`: `x0,y0,x1,y1,…` (mm, **sau flip/rot/offset**, trước scan-area mask). Thêm `uint8[pointCount]` cờ: bit0 = trong scan area, bit1 = foreground (sau trừ nền).
`lidarIndex` ánh xạ theo thứ tự `GET /api/lidars`.

## Output ra ngoài (OutputConfig)
```json
{ "osc":{"enabled":true,"host":"127.0.0.1","port":9000,"rateHz":60},
  "tuio":{"enabled":false,"host":"127.0.0.1","port":3333,"rateHz":60},
  "ws":{"enabled":false,"port":9100},
  "coordinate":{"space":"uv|px","wallWidthPx":1920,"wallHeightPx":1080,"flipY":false} }
```
OSC:
- `/wall/count <int n>`
- `/wall/blob <int id> <float x> <float y> <float sizeMm> <float vx> <float vy>` – 1 message mỗi blob mỗi tick
- `/wall/blob/up <int id>` khi blob mất
- `/wall/zone/<zoneId>/enter|hold|exit <int blobId> <float x> <float y>`
- `/wall/zone/<zoneId>/count <int n>`
TUIO 1.1 `/tuio/2Dcur`: `source`, `alive`, `set`, `fseq`. WS out: broadcast đúng payload `blobs` và `zoneEvent` như trên.
