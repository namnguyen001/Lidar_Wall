# Prompt 07 – Top view hoàn chỉnh (giống video)

Đọc `docs/04` (mục Top view), `docs/00` (F1, F3–F6, F9), skill `references/calibration.md` (phần hiển thị).

## Việc cần làm (`features/topview/`)
1. Canvas HiDPI, rAF + dirty flag, layer đúng thứ tự docs/04.
2. Lưới + vòng 1m/2m/4m có nhãn; trục X đỏ / Y xanh lá; vòng tự co giãn theo zoom.
3. Điểm thô từ `/ws/points`: nền mờ, foreground/in-area sáng (cam/đỏ); nhiều lidar khác màu nhẹ.
4. **Scan area** vàng: chế độ `Free` (kéo 4 góc), `Rect` (kéo chữ nhật), nút `Select Area` / `Zoom`; HUD `Pos, Size (mm), Angle, Ratio`; nút `Apply` (xanh) / `Cancel` (đỏ hồng) → `PUT scan-area` / hoàn tác.
5. **Quad tường** magenta + 4 chấm cyan sau hiệu chỉnh; blob cam đậm + ID.
6. Pan/zoom: wheel, kéo, `Zoom In/Out/Reset`; lưu viewport vào `uiStore`.
7. Hiệu năng: 4 lidar × 1000 điểm giữ ≥ 55 fps; không tạo object theo điểm.
8. Hỗ trợ chọn lidar đang chỉnh (highlight), ẩn/hiện từng lidar.

## Nghiệm thu
- Kéo scan area, bấm Apply → blob ngoài vùng biến mất ngay; Cancel trả về như cũ.
- Test hình học (mm↔canvas, hit-test handle) trong Vitest.
- Quay màn hình ngắn (hoặc ảnh chụp) so với video: bố cục và màu tương đương.
