# Prompt 05 – Zone engine và quản lý zone

Đọc skill `references/zones-and-events.md`, `docs/02` (Zone, zoneEvent, zoneState), `docs/05` (Zone), `docs/04`.

## Backend
1. `core/zones.py`: hit-test rect/circle (có hiệu chỉnh aspect theo wall px)/polygon (ray casting); validate polygon (≥3 điểm, không tự cắt), rect/circle trong giới hạn hợp lý.
2. `services/zone_engine.py`: trạng thái theo cặp (zoneId, blobId); trigger `enter|exit|hold|touch`, `dwellMs`, `repeatMs`, `cooldownMs`, `minBlobs`, `hysteresisUv`, `exclusiveGroup`; blob `lost` khi đang trong zone → `exit` với `reason:"lost"`.
3. API CRUD zone + duplicate + PUT cả danh sách (import); WS `zoneEvent`, `zoneState`.
4. Unit test biên + dwell + hysteresis + lost.

## Frontend (tab Zones)
1. Danh sách zone: bật/tắt, đổi tên, màu, nhân bản, xoá, thứ tự layer.
2. Công cụ vẽ rect/circle/polygon trực tiếp trên khung **wall preview** (tỉ lệ đúng tường) kèm kéo handle, nhập số; undo/redo local (50 bước); optimistic update + rollback.
3. Zone sáng lên khi có blob bên trong (nhận `zoneState`); import/export JSON.
4. `/wall` có tuỳ chọn hiển thị đường viền zone (debug).

## Nghiệm thu
- Simulator: tay đi vào/ra/ở lại trong zone → đúng chuỗi `enter → hold → exit` (có test tự động).
- Tạo 3 loại zone chồng nhau → sự kiện đúng cho từng zone.
- Reload trang: zone còn nguyên (lưu BE), không nhân đôi state ở FE.
