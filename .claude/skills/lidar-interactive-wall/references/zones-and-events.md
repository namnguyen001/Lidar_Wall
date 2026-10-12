# Zones and events

## Zone model (wall UV space)
`id, name, enabled, layer(int), shape, trigger, dwellMs, minBlobs, cooldownMs, output{oscAddress?, tag?}, color`
Shapes (all in UV):
- `rect`: `{x,y,w,h}`
- `circle`: `{cx,cy,r}` where `r` is a fraction of **wall width**; hit-test with aspect correction: `dx*W, dy*H` in px, compare to `r*W`.
- `polygon`: `{points:[[u,v],...]}` ≥3 points, non-self-intersecting (validate), hit via ray casting.
Zones may overlap; an event is emitted for every zone hit. `layer` only affects UI z-order and optional "first hit wins" per zone group (`exclusiveGroup`).

## Trigger modes
- `enter`: emit once when a blob enters.
- `exit`: emit when it leaves.
- `hold`: emit `hold` once after the blob stays ≥ `dwellMs`, then every `repeatMs` if set.
- `touch`: continuous state while inside (for OSC state streams).

## Event state per (zoneId, blobId)
`outside → inside(since) → held(emitted)`. Add hysteresis: shrink radius/rect by `hysteresisUv` (default 0.005) when deciding *leave* to stop flicker on the border.
When a blob is lost while inside → emit `exit` with `reason:"lost"`.

## Event payload (internal & WS)
`{type:"zone", event:"enter|hold|exit", zoneId, blobId, u, v, ts, reason?}`
Zone `count` (blobs inside) is published on every change: `{type:"zoneState", zoneId, count, blobIds:[...]}`.

## Management UX (FE)
List with enable toggle, rename, color, duplicate, delete; draw tools (rect/circle/polygon) directly on the wall preview; drag handles; numeric inputs; import/export JSON; undo/redo (local, max 50).
Backend validates and is the source of truth (`PUT /api/zones/{id}`); FE sends optimistic updates and rolls back on error.
