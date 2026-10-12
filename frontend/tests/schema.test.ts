import { describe, it, expect } from 'vitest'
import { ConfigSchema } from '../src/api/schema'

describe('Config Zod Parser', () => {
  it('parses valid config', () => {
    const valid = {
      version: 1,
      wall: { widthPx: 1920, heightPx: 1080, widthMm: 4000, heightMm: 2250 },
      lidars: [],
      blob: {},
      zones: [{
        id: "z1", name: "test", enabled: true, layer: 0, color: "#fff",
        shape: { type: "rect", x:0, y:0, w:1, h:1 },
        trigger: "enter"
      }],
      output: {},
      ui: {}
    }
    
    const res = ConfigSchema.safeParse(valid)
    expect(res.success).toBe(true)
  })

  it('fails on invalid config', () => {
    const invalid = { version: "v1" } // Version must be number
    const res = ConfigSchema.safeParse(invalid)
    expect(res.success).toBe(false)
  })
})
