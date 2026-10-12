# 01 – Kiến trúc

## Tổng quan
```
 YDLIDAR TEA (TCP 192.168.0.11) ─┐
 YDLIDAR G4  (COM3 @230400)      ─┼─► [Driver threads] ─► latest ScanFrame (slot/lidar)
 Simulator                        ─┘                          │
                                                              ▼
                              ┌────────────── Backend (FastAPI, asyncio) ──────────────┐
                              │ LidarManager  ──► DetectionService (per-lidar pipeline)│
                              │                         │ detections (UV)              │
                              │                         ▼                              │
                              │ FusionTracker (30 Hz tick) ─► ZoneEngine ─► OutputHub  │
                              │ CalibrationService   ConfigStore   PresetStore         │
                              └──────┬───────────────────────────────────────┬─────────┘
                    REST + WS (/ws/events, /ws/points)                        │ OSC / TUIO / WS
                                     ▼                                         ▼
                    Frontend React: /control (điều khiển)            TouchDesigner / Unity
                                    /wall (hiển thị trên tường)
```

## Thành phần backend (`backend/app/`)
```
main.py                 tạo FastAPI app, lifespan (start/stop services)
api/                    routers: lidars, calibration, zones, config, presets, output, ws
core/                   THUẦN: geometry.py, polar.py, scan_area.py, background.py,
                        clustering.py, tracking.py, smoothing.py, homography.py, zones.py
drivers/                base.py, ydlidar_sdk.py, simulator.py, (ydlidar_serial.py fallback)
services/               lidar_manager.py, detection.py, fusion.py, calibration.py,
                        zone_engine.py, output_hub.py, ws_hub.py
models/                 pydantic: config.py, api.py, events.py
storage/                config_store.py (atomic JSON), preset_store.py, background_store.py
output/                 osc.py, tuio.py, ws_out.py
```

## Luồng dữ liệu & luồng (thread)
- Mỗi driver = 1 thread. Ghi `ScanFrame` mới nhất vào slot.
- `DetectionService`: asyncio task mỗi lidar, poll slot (hoặc `loop.call_soon_threadsafe` khi có scan mới). Chạy pipeline numpy (≤ 5 ms). Nặng hơn → `run_in_executor`.
- `FusionTracker`: tick cố định 30 Hz (`asyncio` timer): lấy detections mới nhất của mọi lidar (tuổi ≤ 150 ms) → fuse → track → ZoneEngine → OutputHub.
- `WsHub`: broadcast tới FE. Có backpressure: nếu client chậm, bỏ frame cũ (không xếp hàng).
- `CalibrationService`: máy trạng thái, nhận blob thô theo lidar đang calibrate.

## Hai kênh WebSocket
- `/ws/events` (JSON text): trạng thái lidar, blob, zone event, calibration, lỗi. ≤ 30 Hz cho blob.
- `/ws/points` (binary): điểm quét thô để vẽ top view. ≤ 15 Hz, nén thành Float32 (xem docs/02).
FE `/wall` chỉ cần `/ws/events`.

## Lưu trữ
`data/config.json` (cấu hình chính), `data/presets/*.json`, `data/bg/<lidarId>.npy`, `data/logs/`.
Ghi atomic; backup `config.json.bak` trước khi ghi đè; giữ 10 bản gần nhất trong `data/backups/`.

## Triển khai
Dev: uvicorn + Vite dev server (proxy `/api`, `/ws`). Production: `npm run build`, FastAPI phục vụ `frontend/dist` tại `/`. Chạy bằng 1 lệnh `scripts/start.ps1`.
Cổng mặc định: HTTP 8080; OSC out 9000; TUIO 3333; WS out 9100.
