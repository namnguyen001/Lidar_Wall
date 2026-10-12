# Prompt 08 – Nhiều lidar: coverage, fusion, calibration từng lidar

Đọc skill `references/multi-lidar.md`, `docs/01` (FusionTracker), `docs/05` (coverageUv, overrides).

## Việc cần làm
1. `services/fusion.py`: tick cố định 30 Hz; lấy detections mới nhất mỗi lidar (tuổi ≤ 150 ms); lọc theo `coverageUv`; gộp khi khoảng cách (quy ra mm bằng `wall.widthMm/heightMm`) < `mergeRadiusMm`; vị trí = trung bình có trọng số; ghi `sources`.
2. Tracking **một lần** sau fusion (chuyển tracking từ per-lidar sang fused). Giữ per-lidar chỉ phần cluster/blob thô.
3. Lidar rớt → các lidar khác vẫn chạy; WS báo; FE hiện lỗ hổng coverage (vẽ coverage mờ trên wall preview).
4. Calibration chọn `lidarId`; đích chỉ nằm trong `coverageUv` của lidar đó (hoặc người dùng chọn tay).
5. `overrides.blob` theo lidar (TEA và G4 mật độ điểm khác nhau).
6. FE: panel "Coverage" kéo chỉnh vùng phủ từng lidar trên wall preview; badge lidar offline.
7. Simulator hỗ trợ 2+ lidar nhìn cùng tường để test.

## Nghiệm thu
- Test fusion: 1 tay ở vùng chồng → đúng 1 blob; tay đi xuyên vùng chồng → ID không đổi, nhảy vị trí < 40 mm.
- Rút 1 lidar → blob vùng lidar còn lại vẫn hoạt động; cắm lại → tự phục hồi.
- Phần cứng thật: TEA + G4 cùng hoạt động, đã calibrate riêng, seam test đạt.
