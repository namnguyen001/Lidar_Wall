# Prompt 01 – Scaffold BE + FE + Simulator

Đọc `CLAUDE.md`, `docs/01`, `docs/02`, `docs/03`, `docs/04`, `docs/05`, `config/default.config.json`.

## Việc cần làm
**Backend (`backend/`)**
1. Tạo cấu trúc `app/` đúng docs/01 (`api, core, drivers, services, models, storage, output`), `tests/`, `pyproject` hoặc dùng `requirements.txt` có sẵn, cấu hình `ruff` + `mypy`.
2. `models/config.py`: pydantic v2 khớp `config/config.schema.json` (`extra="forbid"`), có `version`.
3. `storage/config_store.py`: đọc `data/config.json` (nếu chưa có thì copy từ `config/default.config.json`), ghi atomic, backup, debounce.
4. `drivers/base.py`: `ScanFrame`, `DriverStatus`, `LidarDriver` (Protocol) đúng skill/ydlidar-drivers.md.
5. `drivers/simulator.py`: tường thẳng + tối đa 3 tay di chuyển (seed cố định), 10 Hz, nhiễu σ 5 mm.
6. `services/lidar_manager.py`: tạo/khởi động/dừng driver theo config; trạng thái + FPS.
7. API: `GET /api/health`, `GET/PUT /api/config`, `GET/POST/PATCH/DELETE /api/lidars`, `POST /api/lidars/{id}/connect|disconnect` (đúng docs/02).
8. `/ws/events` gửi `hello`, `lidarStatus`; `/ws/points` gửi binary điểm thô đúng định dạng docs/02 (cờ bit tạm = 0).
9. Đặt lidar mặc định chạy **simulator** nếu biến môi trường `LIDAR_FORCE_SIM=1`.

**Frontend (`frontend/`)**
1. Vite + React + TS strict + Tailwind + Zustand + TanStack Query + zod. Proxy `/api` & `/ws` tới `localhost:8080`.
2. Khung trang `/control` (tab rỗng: Lidar | Input | Output | Blob | Zones | Settings) và `/wall` (nền tối).
3. `api/rest.ts`, `api/ws.ts` (reconnect backoff), `api/schemas.ts` (zod cho `hello`, `lidarStatus`).
4. Tab **Lidar**: danh sách lidar + trạng thái + nút Connect/Disconnect; `TopViewCanvas` vẽ vòng 2m/4m và điểm thô từ `/ws/points`.

**Khác**: `scripts/dev.ps1` chạy cả BE và FE; cập nhật mục "Lệnh chuẩn" trong CLAUDE.md nếu khác.

## Ràng buộc
Không code driver YDLIDAR thật ở bước này. Không thêm thư viện ngoài danh sách stack.

## Nghiệm thu
- `LIDAR_FORCE_SIM=1` → mở `/control` thấy điểm quét mô phỏng chuyển động, trạng thái lidar "connected", FPS ≈ 10.
- `pytest -q`, `ruff`, `mypy`, `npm run typecheck`, `npm run lint` xanh. Có test cho config store và frame binary encode/decode.
