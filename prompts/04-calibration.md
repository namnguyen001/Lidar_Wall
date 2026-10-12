# Prompt 04 – Hiệu chỉnh 4 điểm (giống video)

Đọc skill `references/calibration.md`, `docs/02` (mục Hiệu chỉnh + CalibrationState), `docs/04` (trang `/wall`).

## Backend
1. `core/homography.py`: `compute_homography(src_mm, dst_uv)` (4 điểm: `findHomography` method 0; >4: RANSAC), `project`, `residuals_px`, kiểm tra hợp lệ (det, thẳng hàng, góc ngoài vùng).
2. `core/homography.py` hoặc `provisional.py`: H0 từ scan-area quad → UV.
3. `services/calibration.py`: máy trạng thái `IDLE→WAIT_HAND→CAPTURING→…→REVIEW→COMMITTED|CANCELLED|FAILED`. Auto-capture khi `distancePx < 60` và đứng yên `stableFrames=5`; 40 mẫu/điểm, lấy **median**, loại điểm nếu MAD > 25 mm; tay rời > 1.5× bán kính → quay lại WAIT_HAND.
4. Endpoint: `start`, `state`, `capture`, `redo`, `cancel`, `commit` + WS `calibration` (≤ 15 Hz khi đang bắt).
5. Khi `commit`: lưu `calibration` vào lidar, áp dụng ngay cho pipeline (blob chuyển sang `H` thật). `DELETE /api/lidars/{id}/calibration` quay về H0.
6. Chỉ cho 1 phiên hiệu chỉnh tại một thời điểm (`CALIBRATION_BUSY`).

## Frontend
1. Route `/wall`: vẽ đích, đường nét đứt, nhãn `Capturing N samples` / `Distance X px (SPACE to capture)`, tiêu đề + hướng dẫn, phím Space/Esc/F, hiệu ứng vòng phát sáng (cyan; đích hiện tại cam).
2. Tab trong `/control`: nút "Bắt đầu hiệu chỉnh" (chọn lidar), hiển thị state, nút Capture/Cancel/Redo, màn REVIEW với `rmsPx`, `maxPx`, quad magenta + 4 chấm cyan trên top view, nút Commit/Retry.
3. "Test mode": crosshair tại UV của blob để kiểm sai số.

## Nghiệm thu
- Simulator có chế độ "tay ảo đi tới đích": calibration end-to-end ra `rmsPx < 5` (test tự động).
- Phần cứng thật: hoàn tất 4 điểm < 60 s, `rmsPx ≤ 15`, crosshair bám tay.
- Esc huỷ không để lại trạng thái treo; mất lidar giữa chừng → `FAILED` có thông báo.
