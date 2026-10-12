# Multiple lidars

## Strategy
Each lidar `L_k` has its own `H_k` (lidar mm → wall UV) from its own 4-point calibration, and its own Scan Area + background. No lidar-to-lidar pose estimation needed.
Typical setups: (a) several lidars along a long wall, each covering a segment with ~10–20 % overlap; (b) lidars at both ends facing each other to reduce occlusion (a hand shadows another hand).

## Per-lidar coverage
`coverageUv` = rectangle (or polygon) of the wall that lidar is responsible for. Detections outside its coverage (after homography) are dropped, except inside overlap bands.

## Fusion in UV (per tick)
1. Each lidar produces detections `[(u,v,sizeMm,conf)]`.
2. Merge detections from different lidars when `dist(Δ in mm-equivalent) < mergeRadiusMm` (default 60 mm → convert via wall physical width `wall.widthMm`). Fused position = confidence-weighted mean; keep `sources:[lidarIds]`.
3. Track once on fused detections (see pipeline.md §5).
4. If a lidar is down, others continue; UI shows lidar offline badge and coverage hole.

## Timing
Lidars are not synchronised (10 Hz each, phase differs). Use a **fixed fusion tick** (default 30 Hz) that takes each lidar's newest detections (age ≤ 150 ms) rather than waiting for all lidars.

## Mixed models (TEA + G4)
Different rates/density: normalise via per-lidar `minPoints`, `clusterGapMm`, and noise tolerance. Keep per-lidar parameter overrides in config (`lidar.overrides.blob`).

## Calibration order
Calibrate each lidar separately with the wizard (`lidarId` param), restricting targets to its coverage. After all are done, run a **seam test**: walk a hand across the overlap; the fused ID must stay the same (no jump > 40 mm).
