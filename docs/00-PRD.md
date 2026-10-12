# 00 – PRD: Lidar Interactive Wall

## Mục tiêu
Ứng dụng desktop/web (chạy trên Windows) kết nối 1..N LiDAR 2D để biến tường (LED/projection) thành bề mặt cảm ứng đa điểm,
có công cụ hiệu chỉnh nhanh, quản lý vùng quét và vùng tương tác (zone), xuất dữ liệu cho TouchDesigner/Unity/Resolume.

## Người dùng
Kỹ thuật viên lắp đặt (calibration, tinh chỉnh) và nghệ sĩ/creative coder (nhận dữ liệu, thiết kế zone).

## Chức năng suy ra từ video
| # | Chức năng | Mô tả |
|---|---|---|
| F1 | Top view | Nhìn từ trên xuống: vòng khoảng cách 2m/4m…, trục X/Y, điểm quét thô (đỏ/cam), blob (cam đậm) |
| F2 | Tab giao diện | `Lidar | Input | Output | Blob | Zones | Settings` |
| F3 | Flip Axis | Nút Flip X, Flip Y cho từng lidar |
| F4 | Zoom | Zoom In/Out/Reset trên top view |
| F5 | Area Selection | Chọn vùng quét: chế độ `Free` (4 góc tự do) / `Rect`, nút `Select Area` và `Zoom`; hiện Pos, Size (mm), Angle, Ratio |
| F6 | Apply/Cancel | Nút xanh (Apply) và đỏ (Cancel/Reset) cho thay đổi vùng |
| F7 | Presets | Lưu/nạp bộ thông số |
| F8 | Calibration wizard 4 điểm | Hiện đích trên tường, auto-capture khi tay đủ gần, Space = capture ngay, Esc = huỷ, nhãn `Capturing N samples` / `Distance X px` |
| F9 | Hiển thị quad tường | Tứ giác (magenta) 4 góc xanh sau hiệu chỉnh; hình chữ nhật vàng = vùng quét |
| F10 | Multi-touch | Nhiều blob đồng thời với ID ổn định, hiển thị vòng cam trên tường |

## Chức năng bổ sung theo yêu cầu
| # | Chức năng | Mô tả |
|---|---|---|
| F11 | Kết nối lidar | Danh sách thiết bị, thêm/xoá/bật/tắt, trạng thái (state, FPS, lỗi), tự reconnect. Hỗ trợ YDLIDAR **TEA (TCP)** và **G4 (Serial)**, và Simulator |
| F12 | Nhiều lidar | Mỗi lidar có scan area, background, homography, coverage riêng; hợp nhất trong UV |
| F13 | Quản lý Zone | CRUD zone rect/circle/polygon, trigger enter/exit/hold/touch, dwell, nhóm, import/export |
| F14 | Output | OSC, TUIO 1.1, WebSocket JSON; cấu hình host/port/rate; nút test |
| F15 | Background | Học nền, tolerance, re-learn |
| F16 | Chế độ Wall | Route `/wall` toàn màn hình hiển thị đích hiệu chỉnh và vòng cảm ứng trên chính tường |
| F17 | Lưu cấu hình | Tự lưu JSON, export/import, preset |

## Phi chức năng
- Độ trễ chạm → output ≤ 60 ms (không tính mạng ngoài).
- Chạy ổn định ≥ 12 giờ; lidar rớt/cắm lại tự phục hồi.
- 1 lidar: ≤ 15 % CPU một lõi trung bình; hỗ trợ ≥ 4 lidar.
- Giao diện dùng được trên màn hình 1080p và tablet; không cần internet.

## Ngoài phạm vi (v1)
SLAM, 3D, nhận dạng cử chỉ phức tạp, xác thực người dùng, cloud.

## Tiêu chí thành công
Calibrate 4 điểm < 60 giây; sai số RMS ≤ 15 px trên tường 1920 px; hai tay chạm đồng thời giữ ID ổn định; zone phát sự kiện đúng; TouchDesigner nhận OSC/TUIO.
