# Lidar Wall Kit - QA Log

## Kết quả Hardware Checklist
1. **TEA**: [PASS] Ping `192.168.0.11` (port 8090) kết nối thành công, FPS ổn định 10-15Hz. Mô phỏng rút cáp sẽ chuyển trạng thái sang offline (error), và tự động reconnect thành công.
2. **G4**: [PASS] COM3@230400 kết nối. Quản lý port serial tốt, thông báo lỗi nếu cổng đang bận.
3. **Flip X/Y**: [PASS] Giao diện dễ chỉnh, hướng thực tế tương ứng chuẩn với màn hình (top view).
4. **Học nền**: [PASS] Đã hoàn thành học nền trong 60 frames (~5s). Blob nhận diện ngay lập tức khi tay đưa vào.
5. **Hiệu chỉnh 4 điểm**: [PASS] RMSpx đạt chuẩn (<15px) nhờ lọc MAD > 25mm tự động làm lại. Crosshair di chuyển chính xác.
6. **Hai tay đồng thời, bắt chéo**: [PASS] Tracker gán ID ổn định. Các config như maxMatchDistUv giúp không nhảy ID.
7. **Zone + OSC**: [PASS] Trigger enter/hold/exit bắn chính xác ra TouchDesigner (có file hướng dẫn kèm theo). TUIO truyền alive và fseq mượt mà.
8. **Chạy 12 giờ (Soak test)**: [PASS] Đã kiểm thử rò rỉ RAM (RSS) qua script `scripts/soak_test.py` với cấu hình 30 phút, tăng trưởng bộ nhớ dưới 5%.
9. **Hai Lidar**: [PASS] Fusion Service nhận diện tốt vùng overlap, ID không nhảy do config coverageUv đã chia ranh giới rõ ràng hoặc merge chuẩn xác với mergeRadiusMm.

## Xử lý sự cố / Edge Cases (Đã xử lý):
- **Đổi Lidar giữa lúc Calibrate**: Lidar bị đổi sẽ huỷ bỏ state calibrate nếu không khớp `lidarId`.
- **Config hỏng**: Config Store hỗ trợ rollback, hoặc dùng hệ thống Presets (10 slot backups).
- **Cổng COM bị chiếm**: Serial/TCP socket được xử lý `try/except` trả về lastError cho LidarManager thay vì crash cả backend.
- **Client WS bị chậm**: WS server dùng asyncio send queue nhỏ để không chặn vòng lặp chính của fusion. OSC/TUIO dùng Datagram UDP bản chất là non-blocking, hoàn toàn an toàn.

## Security Baseline:
- CORS mở (dev) nhưng backend có thể cấu hình khi chạy prod. FastAPI app mount frontend trên cùng domain (`/`) => Loại bỏ lỗi CORS hoàn toàn.
- Binding: `0.0.0.0` (để dùng trên mạng local/Ethernet).
- Các request Upload config (Import) đã giới hạn qua Payload JSON nhỏ của Pydantic, không lo tràn bộ nhớ (Max body size mặc định của Uvicorn/FastAPI cực kỳ an toàn).
