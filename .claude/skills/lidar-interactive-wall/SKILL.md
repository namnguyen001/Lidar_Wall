---
name: lidar-interactive-wall
description: Domain knowledge for building a LiDAR-based interactive wall app (2D LiDAR touch detection, YDLIDAR TEA/G4 drivers, multi-lidar fusion, 4-point calibration wizard, scan-area selection, zone management, OSC/TUIO output to TouchDesigner). Use this skill whenever the user or task mentions lidar, YDLIDAR, TEA, G4, interactive wall, tường tương tác, vùng quét, scan area, zone, hiệu chỉnh/calibration, blob tracking, homography, TouchDesigner, TUIO, OSC, or touch on LED wall — even if they do not name the skill explicitly.
---

# Lidar Interactive Wall

Build and maintain an app that turns 2D LiDAR scans running parallel to a wall into multi-touch input on that wall.

## Mental model
A 2D LiDAR placed at the wall edge (or in front, scanning a thin plane ~1–5 cm off the wall) returns `(angle, distance)` samples.
A hand touching/near the wall is a small cluster of points inside the **Scan Area**. We turn clusters into **blobs**, track them (stable IDs),
map them to wall UV via a **homography** from a **4-point calibration**, then test them against **zones** and emit events.

## Pipeline (per lidar, per scan)
`driver → polar→xy(mm) → flip/rot/offset → scan-area mask → background subtract → cluster → blob filter → (homography→UV)`
then **fuse all lidars in UV → track (IDs, smoothing) → zone hit-test → output (OSC/TUIO/WS)**.
Details and default numbers: `references/pipeline.md`.

## Workflow when asked to implement something
1. Identify which area it touches and read the matching reference first:
   - Detection / filtering / tracking / smoothing → `references/pipeline.md`
   - 4-point wizard, homography, auto-capture, residual error → `references/calibration.md`
   - TEA / G4 connection, SDK options, reconnect, simulator → `references/ydlidar-drivers.md`
   - Zones, shapes, trigger modes, events → `references/zones-and-events.md`
   - 2+ lidars, overlap, merge, seams → `references/multi-lidar.md`
2. Keep math in `backend/app/core` (pure, tested). Keep hardware in `backend/app/drivers`.
3. Always make the feature work against the **simulator driver** first, then real hardware.
4. Respect the FE↔BE contract in `docs/02-API-CONTRACT.md`; update the contract *before* changing message shapes.

## Non-negotiables
- Units: lidar space = **millimetres**; wall space = **UV [0,1]**, origin top-left, y down. Convert only at the edges.
- Each lidar owns its homography to wall UV (no inter-lidar pose needed). Fuse in UV, then track once.
- Calibration uses a **provisional mapping from the Scan Area quad** so the wizard can show "distance to target" before any homography exists.
- Median of N samples per calibration point (default 40), reject unstable samples.
- Never block the asyncio loop with SDK calls; one thread per driver.
- Hardware facts that are not verified (TEA TCP port, SDK enum names) must be *probed and confirmed with the user*, not assumed.

## Output conventions
OSC defaults: `/wall/blob/<id> x y size state`, `/wall/zone/<zoneId>/<enter|hold|exit> blobId x y`, `/wall/count n`. TUIO 1.1 `/tuio/2Dcur` optional. See `docs/02` for exact payloads.
