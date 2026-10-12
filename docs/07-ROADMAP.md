# 07 – Lộ trình

| Giai đoạn | Prompt | Kết quả |
|---|---|---|
| 0 | 00–01 | Scaffold BE+FE, config, health, WS khung, simulator chạy ra điểm |
| 1 | 02 | Driver YDLIDAR TEA + G4 (đã probe & xác nhận), trạng thái/reconnect |
| 2 | 03 | Pipeline detection: transform, scan area, nền, cluster, blob, tracking |
| 3 | 04 | Calibration 4 điểm (BE state machine + overlay `/wall`) |
| 4 | 05 | Zone engine + quản lý zone |
| 5 | 06–07 | Frontend: shell, tab, top view đầy đủ (flip/zoom/area select/HUD) |
| 6 | 08 | Nhiều lidar: coverage, fusion, calibration từng lidar |
| 7 | 09 | Output OSC/TUIO/WS + mẫu TouchDesigner |
| 8 | 10 | Hardening: preset, backup, log, 12h soak, đóng gói `start.ps1` |

## Definition of Done mỗi giai đoạn
Chạy được bằng Simulator **và** (nếu có phần cứng) bằng thiết bị thật; test xanh; docs/02 khớp; ghi chú còn tồn đọng vào `docs/BACKLOG.md`.

## Rủi ro đã biết
1. Build YDLidar-SDK Python trên Windows có thể khó → có phương án dự phòng (docs/05).
2. Port TCP của TEA chưa xác nhận → probe trước.
3. Nhiễu/phản xạ trên màn hình LED bóng → tinh chỉnh `bgToleranceMm`, `minPoints`.
4. Hai lidar khác mật độ điểm → cần `overrides.blob` theo lidar.
5. Tay che nhau (occlusion) → khuyến nghị lidar hai đầu tường (xem skill/multi-lidar).
