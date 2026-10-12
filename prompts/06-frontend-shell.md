# Prompt 06 – Frontend shell và các tab cấu hình

Đọc `docs/04` (phong cách, cấu trúc), `docs/02`, `docs/00` (F2–F7, F14, F15).

## Việc cần làm
1. Design tokens (CSS variables + Tailwind theme) theo phong cách video: nền navy tối, neon cyan/magenta/vàng/cam; font Rajdhani/JetBrains Mono **tự host**.
2. Layout `/control`: thanh tab trên; panel phải 360–420 px; top view chiếm phần còn lại; banner "Mất kết nối backend".
3. Tab **Lidar**: danh sách lidar, thêm lidar (form theo `kind`: serial/tcp/simulator, nút "Dò kết nối"), bật/tắt, xoá; Flip X / Flip Y; xoay + offset; nút Presets.
4. Tab **Input**: học nền (tiến độ), tolerance, min/max range, nút re-learn.
5. Tab **Blob**: slider clusterGap, minPoints, min/max size, smoothing, lostFrames (áp dụng nóng, debounce 300 ms).
6. Tab **Output**: OSC/TUIO/WS bật/tắt, host/port/rate, nút "Gửi thử".
7. Tab **Settings**: thông tin tường (px/mm), ngôn ngữ, export/import config, danh sách preset (lưu/áp dụng/xoá).
8. i18n `vi.ts`/`en.ts`; mọi control có tooltip + focus ring.

## Ràng buộc
Không tự tính logic miền ở FE. Mọi thay đổi gọi API và phản ánh từ server. Không thêm thư viện UI ngoài Radix.

## Nghiệm thu
- Điều khiển đủ các tab, thay đổi thấy ngay trên top view (flip, range…).
- Test Vitest cho parser zod + store; typecheck/lint xanh; layout dùng tốt ở 1366×768 và 1920×1080.
