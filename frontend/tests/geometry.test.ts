import { describe, it, expect } from 'vitest'
import { toCanvas, toMm, hitTestHandle } from '../src/utils/geometry'

describe('Geometry Utils', () => {
  it('converts mm to canvas and back correctly', () => {
    const w = 800, h = 600
    const vp = { x: 50, y: -20, zoom: 0.5 }
    const mmPoint = { x: 1200, y: -300 }
    
    const canvasPt = toCanvas(mmPoint.x, mmPoint.y, w, h, vp)
    const backToMm = toMm(canvasPt.x, canvasPt.y, w, h, vp)
    
    expect(backToMm.x).toBeCloseTo(mmPoint.x, 3)
    expect(backToMm.y).toBeCloseTo(mmPoint.y, 3)
  })

  it('correctly handles hit testing', () => {
    expect(hitTestHandle(100, 100, 105, 105, 15)).toBe(true) // dist = ~7 < 15
    expect(hitTestHandle(100, 100, 120, 100, 15)).toBe(false) // dist = 20 > 15
  })
})
