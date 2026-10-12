# Hướng dẫn kết nối Lidar Wall Kit với TouchDesigner

## Cách 1: Sử dụng TUIO (Khuyên dùng)
TUIO là giao thức chuẩn để nhận đa điểm chạm (multi-touch). Lidar Wall Kit hỗ trợ TUIO 1.1 (2Dcur).

1. Bật TUIO trong cấu hình `Output` của Lidar Wall Kit (Host: 127.0.0.1, Port: 3333).
2. Mở TouchDesigner.
3. Tạo một `TUIO In DAT`. Đặt Network Port là `3333`.
4. Để chuyển sang dạng channel tiện cho việc render, tạo một `DAT to CHOP`, nối `TUIO In DAT` vào.
   - Chọn **Output**: Channel per Column
   - **First Row**: is Names
5. Bây giờ bạn đã có các giá trị toạ độ `u`, `v` của từng điểm chạm (từ 0.0 đến 1.0) và có thể nối vào `Circle TOP`, `Transform TOP` hoặc `Instancing` tuỳ ý.

## Cách 2: Sử dụng OSC
Lidar Wall Kit phát OSC linh hoạt hơn TUIO, hỗ trợ cả zone event và toạ độ theo px (pixel).

1. Bật OSC trong phần `Output` (Host: 127.0.0.1, Port: 9000).
2. Mở TouchDesigner, tạo `OSC In DAT`, Port `9000`.
3. Tạo một `Script CHOP` và nối `OSC In DAT` vào `Script CHOP`.
4. Nhấp vào nút `Edit...` trên `Script CHOP` và nhập đoạn code xử lý sự kiện:

```python
# Script CHOP mẫu nhận /wall/blob
def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, source, *args):
    addr = message[0]
    args = message[1:]
    
    if addr == "/wall/blob":
        blob_id, x, y, size_mm, vx, vy = args
        # Ví dụ: cập nhật channel
        # op('constant1').par.value0 = x
        pass
    elif addr == "/wall/zone/enter":
        zone_id, blob_id, x, y = args
        # ...
```
*(Để Script CHOP xử lý tuỳ ý, bạn có thể tạo một `OSC In CHOP` và gõ tên OSC address `/wall/blob*` để nhận các giá trị số tự động, nhưng Script DAT giúp bạn bắt chính xác sự kiện click/enter/hold)*.

## Phối hợp hiển thị
Sử dụng giá trị UV (nếu Output Coordinate là `uv`) để làm toạ độ X, Y cho `Circle TOP` hoặc `Geo COMP` trong hệ Toạ độ của TouchDesigner (0 đến 1, hoặc -1 đến 1 nếu chuyển đổi thêm).
