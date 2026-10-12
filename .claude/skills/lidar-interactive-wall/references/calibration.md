# 4-point calibration (mirrors the video)

## Goal
Find homography `H` (3×3) mapping a lidar point (mm) → wall UV. One `H` per lidar.

## Provisional mapping (needed for "distance to target")
Before calibration exists, build `H0` from the **Scan Area quad corners** (mm) to the wall rectangle corners (UV `[0,0],[1,0],[1,1],[0,1]`), order: TL, TR, BR, BL.
Use `H0` to project the live blob → UV so the UI can draw the line hand→target and show `Distance NNN px` (UV distance × wall pixel size).

## Targets
Default UV: `(0.1,0.1) (0.9,0.1) (0.9,0.9) (0.1,0.9)`; configurable. For long walls with several lidars, each lidar calibrates only the targets inside its own coverage (segment of wall); use `coverageUv` rectangle to place targets inside it. More than 4 points allowed (use RANSAC, ≥4).

## State machine (backend owns it; FE only renders)
`IDLE → WAIT_HAND(i) → CAPTURING(i, n/N) → NEXT → ... → COMPUTE → REVIEW → COMMITTED | CANCELLED | FAILED`
- `WAIT_HAND`: choose the nearest active blob (only one expected). Distance to target in px < `autoCaptureRadiusPx` (default 60) AND speed < `stableSpeedUvPerS` (0.05) for `stableFrames` (5) → go `CAPTURING`.
- `CAPTURING`: store raw lidar-mm centroid each scan until N (default 40). If the hand leaves radius ×1.5 → back to `WAIT_HAND` (discard).
- Manual: `POST /calibration/capture` (Space in UI) forces capture with current blob; `cancel` (Esc) aborts.
- Point result = **median** of samples per axis; reject point if spread (MAD) > 25 mm → ask user to redo that point.
- `COMPUTE`: `cv2.findHomography(src_mm, dst_uv, method=0)` for 4 pts, RANSAC if > 4. Compute residual: project src → UV, error in px = ‖ΔUV‖·wallSize. Report `rmsPx`, `maxPx`.
- `REVIEW`: show the calibrated wall quad (magenta in video) with 4 handles + residuals. Accept if `rmsPx <= 15` (warn above, block above 40). User commits or retries. On commit persist `H`, samples, timestamp.

## Validation
- Sanity: `det(H)` not ~0, corners map inside [-0.1,1.1] UV, points not collinear (area of 4 pts quad > threshold).
- After commit, live touch should land within ~1 cm of the finger; provide a "Test mode" showing a crosshair at the mapped UV.

## Visual language on the wall (`/wall` route)
Glowing cyan ring at target, orange target for current point, number badge, dashed cyan line target↔hand with label `Capturing 35 samples` / `Distance 125px (SPACE to capture)`, title `Calibrating Point 2/4`, hint text `Move hand to orange point. Auto-capture when close enough | SPACE for instant capture | ESC to cancel`.
