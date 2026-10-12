export function toCanvas(mmX: number, mmY: number, w: number, h: number, vp: { x: number, y: number, zoom: number }) {
  const scale = vp.zoom
  const cx = w / 2 + vp.x
  const cy = h / 2 + vp.y
  return { x: cx + mmX * scale, y: cy - mmY * scale }
}

export function toMm(cx: number, cy: number, w: number, h: number, vp: { x: number, y: number, zoom: number }) {
  const scale = vp.zoom
  const originX = w / 2 + vp.x
  const originY = h / 2 + vp.y
  return { x: (cx - originX) / scale, y: -(cy - originY) / scale }
}

export function hitTestHandle(cx: number, cy: number, handlePxX: number, handlePxY: number, tolerancePx = 15) {
  return Math.hypot(cx - handlePxX, cy - handlePxY) < tolerancePx
}
