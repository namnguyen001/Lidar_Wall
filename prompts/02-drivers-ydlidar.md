# Prompt 02 – Driver YDLIDAR TEA (TCP) và G4 (Serial)

Đọc skill `references/ydlidar-drivers.md`, `docs/05` (mục Thiết bị YDLIDAR), `docs/03`.

Phần cứng: **TEA** `192.168.0.11` (port TCP chưa xác nhận), **G4** `COM3` @ `230400`.

## Bước A – Probe (làm TRƯỚC, dừng lại hỏi tôi)
1. Viết `scripts/probe_ydlidar.py`:
   - In `dir(ydlidar)` (nếu import được) để xác nhận tên hằng số (`TYPE_TOF`, `YDLIDAR_TYPE_TCP`, …).
   - TCP connect thử `192.168.0.11` với danh sách port ứng viên (8000 trước) timeout 1 s, in kết quả.
   - Với G4: mở `COM3@230400`, đọc vài vòng, in số điểm/vòng, góc min/max, range min/max, tần số quét thực đo.
   - Với TEA (nếu SDK dùng được): tương tự.
2. Hướng dẫn tôi cách chạy từng phần. **Dừng lại, chờ tôi dán kết quả**. Không đoán thông số rồi code tiếp.
3. Nếu `import ydlidar` lỗi: hướng dẫn build SDK trên Windows (docs/05) và đề xuất phương án dự phòng; hỏi tôi chọn.

## Bước B – Driver (sau khi tôi xác nhận)
1. `drivers/ydlidar_sdk.py`: `YdlidarSdkDriver(cfg)` hỗ trợ `kind: serial|tcp`, thread riêng, đổi **m→mm, giữ rad**, loại điểm `range<=0`.
2. Reconnect backoff 1→10 s, status chuẩn, `stop()` sạch (`turnOff`, `disconnecting`), phát hiện COM bận → thông báo rõ.
3. Factory chọn driver theo `connection.kind` (`serial|tcp|simulator`).
4. API: `GET /api/serial-ports`, `GET /api/lidars/probe`.
5. Test: driver giả (mock `ydlidar`) để kiểm vòng đời, reconnect, chuyển đơn vị.

## Nghiệm thu
- Với phần cứng thật: top view hiển thị điểm của TEA và G4; rút cáp/USB → `error` → cắm lại tự `connected`.
- Có thể chạy cả 2 lidar cùng lúc, FPS từng lidar hiển thị đúng.
- Mọi test xanh; docs/05 được cập nhật với thông số đã xác nhận (port TEA, tần số…).
