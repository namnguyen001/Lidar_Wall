# Prompt 03 – Pipeline phát hiện (core thuần)

Đọc skill `references/pipeline.md`, `docs/03` (phần core), `docs/06` (bảng unit test).

## Việc cần làm (trong `backend/app/core/` + service)
1. `polar.py`: polar→xy(mm) vector hoá, lọc range; `transform.py`: flipX, flipY, rotation, offset đúng thứ tự.
2. `scan_area.py`: mask điểm trong quad/rect; validate quad lồi hợp lệ; `PUT /api/lidars/{id}/scan-area`.
3. `background.py`: học nền theo bin góc 0.5° (median), `is_foreground`; lưu `data/bg/<id>.npy`; `POST /api/lidars/{id}/background/learn` + sự kiện WS `bgLearn`.
4. `clustering.py`: gom cụm theo thứ tự góc với `clusterGapMm`, `minPoints`; centroid, `sizeMm`; lọc min/max size.
5. `smoothing.py` (One-Euro), `tracking.py` (Hungarian hoặc greedy, vòng đời new→active→lost, ID tăng dần không tái dùng).
6. `services/detection.py`: chạy pipeline cho mỗi lidar; xuất `rawBlobs` (mm) lên WS; cập nhật cờ bit trong `/ws/points` (trong scan area, foreground).
7. Tạm thời nếu chưa có homography: dùng ánh xạ tạm (scan-area quad → UV) và phát `blobs` ở UV (đây cũng là H0 dùng cho calibration).
8. Đo thời gian mỗi bước, log P95.

## Ràng buộc
Không dùng sklearn/DBSCAN. Không vòng lặp Python trên từng điểm nếu vector hoá được. Mọi ngưỡng lấy từ config (`blob`, `overrides`).

## Nghiệm thu
- Simulator `two_hands` và `cross`: 2 blob, ID giữ nguyên khi giao nhau; mất tay → blob `lost` rồi xoá sau `lostFrames`.
- Unit test theo bảng docs/06 (polar, transform, scan area, background, clustering, tracking) xanh; xử lý ≤ 5 ms/scan (log).
- FE (có thể tạm): top view tô điểm foreground sáng hơn và vẽ blob.
