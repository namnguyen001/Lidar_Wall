import { z } from 'zod'

export const helloSchema = z.object({
  serverVersion: z.string(),
  config: z.unknown()
})

export const lidarStatusSchema = z.object({
  id: z.string(),
  state: z.string(),
  fps: z.number(),
  scanCount: z.number(),
  lastError: z.string().optional().nullable()
})

export const wsEventSchema = z.object({
  v: z.number(),
  type: z.string(),
  ts: z.number(),
  seq: z.number().optional(),
  data: z.unknown()
})
