# 03 – Quy định Backend

## Môi trường
Python 3.11+, venv trong `backend/.venv`. Windows 10/11 là chính. Dependency khoá bằng `requirements.txt` (hoặc `pyproject.toml` nếu chuyển, hỏi trước).
Lint/format: `ruff` (line length 100). Kiểu: `mypy --strict` cho `app/core` và `app/models`, cấu hình lỏng hơn cho `drivers`.

## Cấu trúc & phân tầng (phụ thuộc chỉ đi xuống)
`api → services → core / drivers / storage / output` · `models` dùng chung. **`core` không import `services`, `api`, `drivers`.**
- `api/*`: mỏng; chỉ parse/validate, gọi service, trả model. Không chứa logic nghiệp vụ.
- `services/*`: điều phối, giữ state runtime, chạy asyncio task.
- `core/*`: hàm thuần numpy/OpenCV; mỗi hàm có docstring nêu đơn vị và shape mảng.
- `drivers/*`: chỉ lo kết nối/đọc dữ liệu → trả `ScanFrame` đã đổi sang **mm + radian**.

## Quy ước code
- Type hint đầy đủ; dataclass/pydantic cho cấu trúc dữ liệu; không dùng dict "tuỳ ý" vượt ranh giới module.
- Tên: `snake_case` hàm/biến, `PascalCase` lớp; hậu tố đơn vị khi mơ hồ: `gap_mm`, `angle_rad`, `dist_px`, `uv`.
- Không `print`; dùng `logging` (logger theo module), kèm `lidar_id` (dùng `LoggerAdapter` hoặc `extra`). Mức: DEBUG pipeline, INFO vòng đời, WARNING phục hồi được, ERROR cần can thiệp.
- Không `except Exception: pass`. Bắt đúng loại, log, và hoặc xử lý hoặc re-raise.
- Không global mutable state; services tạo trong `lifespan`, truyền qua `Depends`/`app.state`.
- Hằng số/ngưỡng: lấy từ config, không số "ma thuật" rải trong code (đặt tên + docstring nếu bắt buộc).

## Asyncio & thread
- Không gọi hàm chặn (SDK, serial, file lớn, cv2 nặng) trong event loop. Dùng thread driver hoặc `run_in_executor`.
- Dữ liệu từ thread sang loop: `loop.call_soon_threadsafe` hoặc slot có lock. Không chia sẻ mảng numpy đang bị ghi.
- Mọi task nền có tên, được huỷ sạch ở shutdown (`lifespan`), không "fire and forget" mà không giữ tham chiếu.

## Config & lưu trữ
- Pydantic v2 `model_config = ConfigDict(extra="forbid")` cho config; có `version` + hàm migrate khi đổi schema.
- Ghi atomic: ghi `*.tmp` → `os.replace`. Backup trước khi ghi đè. Debounce ghi (≥ 500 ms) khi nhận nhiều PATCH liên tiếp.
- Thay đổi config hợp lệ → áp dụng nóng (hot-reload) cho service liên quan, không cần restart. Thông số kết nối lidar đổi → reconnect driver đó.

## API
- Tuân thủ docs/02 tuyệt đối (tên trường, mã lỗi). Response model khai báo rõ (`response_model`).
- Validate đầu vào: góc ngoài tường, polygon tự cắt, `r` âm… → 422 `VALIDATION_ERROR` kèm `details`.
- Idempotent khi hợp lý (connect khi đã connected → trả trạng thái hiện tại).
- OpenAPI phải sạch (có tags, summary). `GET /api/health` luôn nhanh (< 10 ms).

## Hiệu năng
Ngân sách mỗi scan mỗi lidar ≤ 5 ms (đo bằng `time.perf_counter`, log P95 mỗi 10 s ở DEBUG). Tránh vòng lặp Python trên từng điểm khi vector hoá được. Không cấp phát lớn trong vòng nóng.
WS: tick đóng gói ≤ 30 Hz; client chậm → bỏ frame, không tăng bộ nhớ.

## Phục hồi lỗi
- Driver rớt → status `error`, reconnect backoff 1→10 s; không làm sập pipeline các lidar khác.
- Output (OSC/TUIO/WS) lỗi gửi → log giới hạn tần suất, không chặn vòng xử lý.
- Config hỏng khi khởi động → nạp backup gần nhất, cảnh báo qua WS `error`.

## Bảo mật cơ bản
Mặc định bind `127.0.0.1`; cho phép `0.0.0.0` qua cấu hình. CORS chỉ origin dev/prod đã khai báo. Không log dữ liệu nhạy cảm. Giới hạn kích thước upload import (≤ 2 MB).

## Test (tối thiểu)
- Unit cho `core/*`: polar, flip/rot, scan-area mask, clustering, tracking, homography (điểm biết trước), zones hit-test (biên).
- Integration: simulator → pipeline → WS (dùng `httpx` + `websockets`).
- Mỗi PR/phiên: `ruff check`, `mypy`, `pytest -q` phải xanh.

## Definition of Done (BE)
Chạy được với Simulator; có test; docs/02 khớp; log rõ; không warning; config mới có giá trị mặc định + schema cập nhật.
