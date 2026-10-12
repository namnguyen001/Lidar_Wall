# 06 – Kiểm thử & QA

## Simulator
`SimulatorDriver` bắt buộc. Cấu hình: số tay (0–3), tốc độ, nhiễu σ (mm), khoảng cách tường, seed. Kịch bản có sẵn: `static`, `swipe` (1 tay quét ngang), `two_hands`, `cross` (2 tay giao nhau – kiểm ID), `dropout` (lidar ngắt 5 s – kiểm reconnect).

## Unit test (backend/tests/core)
| Khu vực | Ca kiểm |
|---|---|
| polar | góc 0, ±π/2, π; r=0/NaN bị loại |
| transform | flipX/flipY/rotation/offset đúng thứ tự |
| scan area | điểm trong/ngoài/trên cạnh; quad lõm bị từ chối |
| background | học → điểm gần hơn bg−tol là foreground; không lọt nhiễu ±tol |
| clustering | tách 2 cụm cách > gap; gộp khi < gap; minPoints |
| tracking | ID giữ khi 2 blob đi ngang; lost→recover trong lostFrames; ID không tái dùng |
| homography | 4 điểm biết trước → sai số ≈ 0; nhiễu 5 mm → RMS < ngưỡng; điểm thẳng hàng → lỗi |
| zones | biên rect/circle(aspect)/polygon; hysteresis; dwell; exit khi blob lost |
| fusion | 2 lidar thấy cùng 1 tay → 1 blob; tay ở vùng chồng → ID không nhảy |

## Integration
- Simulator → pipeline → `/ws/events`: blob xuất hiện ≤ 200 ms sau khi tay xuất hiện.
- Calibration end-to-end bằng "tay ảo" của simulator đi tới 4 đích → `rmsPx` < 5.
- Config: ghi/đọc/migrate; file hỏng → nạp backup.
- OSC: dùng `python-osc` server giả nhận và kiểm payload khớp docs/02.

## Checklist phần cứng (làm tay, ghi kết quả vào `docs/qa-log.md`)
1. TEA: ping `192.168.0.11`, kết nối từ app, FPS hiển thị ≈ danh định, rút cáp → trạng thái `error` → cắm lại → tự `connected` ≤ 15 s.
2. G4: COM3@230400 kết nối; đóng app khác đang giữ COM3 → thông báo lỗi dễ hiểu.
3. Flip X/Y đúng hướng khi vẫy tay (tay trái trên tường = trái trên top view sau khi chỉnh).
4. Học nền khi không ai đứng gần; tay chạm → blob xuất hiện, bỏ tay → biến mất.
5. Hiệu chỉnh 4 điểm < 60 s, `rmsPx ≤ 15`; test crosshair bám tay trong ~1 cm tại 9 điểm lưới.
6. Hai tay đồng thời, bắt chéo → ID ổn định.
7. Zone: enter/hold/exit đúng; OSC nhận được trong TouchDesigner (`OSC In DAT`/`TUIO In`).
8. Chạy 12 giờ: không rò bộ nhớ (RSS tăng < 5 %), CPU ổn định.
9. Hai lidar: đi dọc vùng chồng, ID không nhảy.

## Chất lượng
CI cục bộ (script `scripts/check.ps1`): `ruff`, `mypy`, `pytest -q`, `npm run typecheck`, `npm run lint`, `npm test`. Không gộp thay đổi khi đỏ.
