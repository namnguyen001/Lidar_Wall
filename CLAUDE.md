# CLAUDE.md – Lidar Interactive Wall

Bạn đang xây **ứng dụng tường tương tác LiDAR**: đọc 1..N LiDAR 2D (YDLIDAR TEA qua TCP 192.168.0.11, YDLIDAR G4 qua COM3@230400),
phát hiện tay/người chạm tường, hiệu chỉnh 4 điểm sang toạ độ tường, quản lý Scan Area và Zone, xuất OSC/TUIO/WebSocket (cho TouchDesigner, Unity…).

## Đọc trước khi code (theo thứ tự)
1. Skill `lidar-interactive-wall` (`.claude/skills/...`) – kiến thức miền, đọc `references/` khi đụng phần liên quan.
2. `docs/01-ARCHITECTURE.md` và `docs/02-API-CONTRACT.md` – hợp đồng FE↔BE. **Không tự ý đổi.**
3. `docs/03-BACKEND-RULES.md` khi sửa `backend/`; `docs/04-FRONTEND-RULES.md` khi sửa `frontend/`.

## Stack cố định
- **Backend**: Python 3.11+, FastAPI, asyncio, pydantic v2, numpy, OpenCV (homography), python-osc. Windows là môi trường chính.
- **Frontend**: React 18 + TypeScript (strict) + Vite + Zustand + TanStack Query + Tailwind. Vẽ top-view bằng **Canvas 2D** (không dùng thư viện chart).
- Không thêm thư viện lớn khi chưa hỏi. Không đổi stack.

## Quy tắc vàng
1. **Hệ toạ độ**: lidar = mm (x phải, y về phía trước); tường = UV 0..1, gốc trên-trái, y xuống. Mọi API/WS dùng đúng đơn vị này; đổi đơn vị chỉ ở biên (UI hiển thị).
2. **Core thuần (pure)**: `backend/app/core/*` không I/O, không global state, có type hint và unit test. Driver/IO nằm ngoài core.
3. **Driver chạy thread riêng** (SDK chặn); đẩy scan mới nhất qua slot an toàn luồng. Không gọi SDK trong event loop.
4. **Có Simulator driver** từ ngày đầu để dev/test không cần phần cứng. Mọi tính năng phải chạy được với simulator.
5. **Mỗi lidar có homography riêng về UV tường**; hợp nhất nhiều lidar trong không gian UV, rồi tracking một lần (xem skill → multi-lidar).
6. **Config là nguồn sự thật**: lưu `config/*.json`, ghi atomic (ghi file tạm rồi rename), validate bằng pydantic. FE không giữ state trùng lặp với BE.
7. **Không hardcode** IP, COM, ngưỡng, kích thước tường. Mọi thông số nằm trong config.
8. **Không nuốt lỗi**: log có ngữ cảnh (lidar id), trả mã lỗi chuẩn (docs/02). Lidar rớt phải tự reconnect (backoff) và báo trạng thái lên UI.
9. **Hiệu năng**: xử lý ≤ 5 ms/scan/lidar; stream FE ≤ 30 Hz; không cấp phát vòng lặp nóng khi có thể dùng numpy vector hoá.
10. Làm **từng bước nhỏ**, chạy test + lint sau mỗi bước, tóm tắt thay đổi và việc chưa làm cuối phiên.

## Khi không chắc
- Thông số phần cứng YDLIDAR chưa chắc → viết script dò trong `scripts/` và **hỏi người dùng xác nhận**, đừng đoán rồi code tiếp.
- Mâu thuẫn giữa docs → docs/02 (contract) thắng, sau đó docs/05 (data models).

## Lệnh chuẩn (cập nhật khi scaffold xong)
- **Dev (chạy cả BE & FE, tự bật Simulator)**: `.\scripts\dev.ps1` (chạy trên PowerShell)
- BE (thủ công): `cd backend`, `.\.venv\Scripts\activate`, `uvicorn app.main:app --reload`
- BE test: `cd backend`, `pytest -q` · lint: `ruff check .` và `mypy app`
- FE (thủ công): `cd frontend`, `npm run dev` · `npm run typecheck && npm run lint`
