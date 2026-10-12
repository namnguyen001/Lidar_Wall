import { z } from 'zod'

export const TransformSchema = z.object({
  flipX: z.boolean(),
  flipY: z.boolean(),
  rotationDeg: z.number(),
  offsetMm: z.tuple([z.number(), z.number()])
})

export const ShapeRectSchema = z.object({
  type: z.literal('rect'),
  x: z.number(), y: z.number(), w: z.number(), h: z.number()
})

export const ZoneSchema = z.object({
  id: z.string(),
  name: z.string(),
  enabled: z.boolean(),
  layer: z.number(),
  color: z.string(),
  shape: z.any(), // Simplified
  trigger: z.enum(['enter', 'exit', 'hold', 'touch']),
})

export const ConfigSchema = z.object({
  version: z.number(),
  wall: z.object({
    widthPx: z.number(),
    heightPx: z.number(),
    widthMm: z.number(),
    heightMm: z.number(),
  }),
  lidars: z.array(z.any()),
  blob: z.any(),
  zones: z.array(ZoneSchema),
  output: z.any(),
  ui: z.any()
})

export type Config = z.infer<typeof ConfigSchema>
