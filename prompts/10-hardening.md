# Prompt 10 – Hardening và đóng gói

Đọc `docs/06` (checklist phần cứng), `docs/03` (phục hồi lỗi), `docs/07` (rủi ro).

## Việc cần làm
1. Preset: lưu/áp dụng/xoá (có/không kèm calibration) + backup tự động `data/backups/` (giữ 10 bản).
2. Log xoay vòng `data/logs/`; trang "Chẩn đoán" trong Settings: trạng thái lidar, FPS, P95 xử lý, lỗi gần nhất, nút tải log.
3. Soak test script: chạy simulator 12 h (rút gọn 30 phút khi CI), đo RSS/CPU; sửa rò rỉ nếu có.
4. Xử lý edge case: đổi lidar giữa lúc calibrate, config hỏng, cổng bị chiếm, mạng TEA chập chờn, client WS chậm.
5. `frontend build` được phục vụ bởi FastAPI tại `/`; `scripts/start.ps1` một lệnh chạy production; `scripts/check.ps1` chạy toàn bộ kiểm tra.
6. Cập nhật docs (README, docs/05 thông số thật, `docs/qa-log.md` kết quả checklist phần cứng).
7. Rà soát bảo mật cơ bản (bind địa chỉ, CORS, giới hạn upload).

## Nghiệm thu
- Checklist phần cứng docs/06 đạt, ghi lại trong `docs/qa-log.md`.
- Chạy liên tục ≥ 12 giờ ổn định (RSS tăng < 5 %).
- `scripts/check.ps1` xanh; tôi khởi động bằng `scripts/start.ps1` và dùng được ngay.
