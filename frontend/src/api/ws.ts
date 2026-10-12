import { create } from 'zustand'
import { wsEventSchema, lidarStatusSchema } from './schemas'

interface WsState {
  eventsConnected: boolean
  pointsConnected: boolean
  lidarStatuses: Record<string, any>
  calibrationState: any
  connectEvents: () => void
  connectPoints: () => void
}

export const useWsStore = create<WsState>((set, get) => ({
  eventsConnected: false,
  pointsConnected: false,
  lidarStatuses: {},
  
  calibrationState: null as any,
  
  connectEvents: () => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/events`)
    ws.onopen = () => set({ eventsConnected: true })
    ws.onclose = () => {
      set({ eventsConnected: false })
      setTimeout(get().connectEvents, 1000) // backoff
    }
    ws.onmessage = (e) => {
      let message: unknown
      try {
        message = JSON.parse(e.data)
      } catch (error) {
        console.warn('Ignoring invalid WebSocket JSON message', error)
        return
      }
      const result = wsEventSchema.safeParse(message)
      if (!result.success) {
        console.warn('Ignoring invalid WebSocket event', result.error)
        return
      }
      const parsed = result.data
      if (parsed.type === 'lidarStatus') {
        const status = lidarStatusSchema.safeParse(parsed.data)
        if (!status.success) {
          console.warn('Ignoring invalid lidar status event', status.error)
          return
        }
        const st = status.data
        set((state) => ({ lidarStatuses: { ...state.lidarStatuses, [st.id]: st } }))
      } else if (parsed.type === 'calibration') {
        set({ calibrationState: parsed.data })
      } else if (parsed.type === 'blobs') {
        const raw = parsed.data as any
        const list = Array.isArray(raw) ? raw : (Array.isArray(raw?.blobs) ? raw.blobs : [])
        window.dispatchEvent(new CustomEvent('blobs', { detail: list }))
      } else if (parsed.type === 'rawBlobs') {
        window.dispatchEvent(new CustomEvent(parsed.type, { detail: parsed.data }))
      }
    }
  },
  
  connectPoints: () => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/points`)
    ws.binaryType = 'arraybuffer'
    ws.onopen = () => set({ pointsConnected: true })
    ws.onclose = () => {
      set({ pointsConnected: false })
      setTimeout(get().connectPoints, 1000)
    }
    ws.onmessage = (e) => {
      // Decode binary frame here and dispatch to Zustand or callback
      if (e.data instanceof ArrayBuffer) {
        // Just trigger event for canvas
        window.dispatchEvent(new CustomEvent('lidar-points', { detail: e.data }))
      }
    }
  }
}))
