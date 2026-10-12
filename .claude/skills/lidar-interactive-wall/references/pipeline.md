# Detection pipeline

## 1. Polar → XY (mm)
`x = r*cos(θ)`, `y = r*sin(θ)` with r in mm. YDLIDAR SDK reports **range in metres and angle in radians** → convert at the driver boundary.
Drop points with `r <= 0`, `r < minRange`, `r > maxRange`, NaN. Then apply per-lidar: `flipX`, `flipY`, `rotationDeg`, `offsetMm` (in this order).
Angle zero/direction differs by model and mounting → the user fixes it with Flip X/Flip Y + rotation in the UI (as in the video), never by hardcoding.

## 2. Scan Area mask
Scan Area = quad (4 points, mm, lidar space, "Free" mode) or axis-aligned rect. Keep points inside (use `cv2.pointPolygonTest` or a vectorised cross-product test). Everything else is ignored — this removes the floor, walls, people far away.

## 3. Background subtraction
- Learn: collect K scans (default 60, ≈6 s @10 Hz) while nobody touches. Bin by angle (resolution 0.5°) and store per-bin **median range**.
- Run: a point is foreground if `range < bg[bin] - tolMm` (default 40 mm) i.e. something is *closer* than the static background.
- Allow re-learn from UI; persist the model per lidar (`data/bg/<lidarId>.npy`), invalidate if lidar config changes.
- For a lidar scanning along the wall the "background" is the wall line; the touching hand shows as points in front of it. Works the same way.

## 4. Clustering (don't use DBSCAN – scans are ordered)
Walk points sorted by angle; start a new cluster when Euclidean gap to previous point > `clusterGapMm` (default 80) or the angle gap is large.
Keep clusters with `>= minPoints` (default 2; G4 has low density at distance, so do **not** raise blindly).
Cluster centroid = mean of points (or median if `robustCentroid`). Blob size = max extent (mm).
Filter: `minSizeMm` (30) ≤ size ≤ `maxSizeMm` (300). Reject larger → bodies/objects (optionally report as `kind:"body"`).

## 5. Tracking (after fusion, in UV)
- Association: Hungarian (or greedy nearest) with `maxMatchDistUv` (default 0.08); cost = distance.
- Lifecycle: `new` (age<`confirmFrames`=2, not emitted) → `active` → `lost` (kept `lostFrames`=3 predicting position) → removed.
- IDs: monotonically increasing ints, never reused within a session.
- Smoothing: One-Euro filter per blob (`minCutoff=1.0`, `beta=0.02`, `dCutoff=1.0`). Expose `smoothing` 0..1 mapped to these.
- Velocity (UV/s) is output for effects.

## 6. Performance notes
Vectorise steps 1–3 with numpy. Step 4 loop over ≤ ~2000 points is fine in Python if kept simple; if > 5 ms, use numpy diff + `np.split`.
Pre-allocate arrays per lidar; reuse.

## 7. Defaults (config.blob / config.input)
| key | default |
|---|---|
| bgLearnScans | 60 |
| bgToleranceMm | 40 |
| clusterGapMm | 80 |
| minPoints | 2 |
| minSizeMm / maxSizeMm | 30 / 300 |
| confirmFrames / lostFrames | 2 / 3 |
| maxMatchDistUv | 0.08 |
| smoothing | 0.4 |
