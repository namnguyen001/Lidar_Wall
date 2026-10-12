import os

files = {
    "src/index.css": """
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-dark: #0f172a;
  --accent-cyan: #22D3EE;
  --accent-magenta: #E040FB;
  --accent-yellow: #FACC15;
  --accent-orange: #FB923C;
  --accent-red: #F43F5E;
}

body {
  background-color: var(--bg-dark);
  color: white;
  margin: 0;
  font-family: 'Inter', system-ui, sans-serif;
}
""",
    "src/main.tsx": """
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
""",
    "src/App.tsx": """
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ControlPage from './routes/ControlPage'
import WallPage from './routes/WallPage'
import { useWsStore } from './api/ws'
import { useEffect } from 'react'

export default function App() {
  const { connectEvents, connectPoints } = useWsStore()
  
  useEffect(() => {
    connectEvents()
    connectPoints()
  }, [connectEvents, connectPoints])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/control" element={<ControlPage />} />
        <Route path="/wall" element={<WallPage />} />
        <Route path="*" element={<ControlPage />} />
      </Routes>
    </BrowserRouter>
  )
}
""",
    "src/api/schemas.ts": """
import { z } from 'zod'

export const helloSchema = z.object({
  serverVersion: z.string(),
  config: z.any()
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
  data: z.any()
})
""",
    "src/api/rest.ts": """
const API_URL = '/api'

export async function fetchHealth() {
  const res = await fetch(`${API_URL}/health`)
  return res.json()
}

export async function fetchLidars() {
  const res = await fetch(`${API_URL}/lidars`)
  return res.json()
}

export async function connectLidar(id: string) {
  const res = await fetch(`${API_URL}/lidars/${id}/connect`, { method: 'POST' })
  return res.json()
}

export async function disconnectLidar(id: string) {
  const res = await fetch(`${API_URL}/lidars/${id}/disconnect`, { method: 'POST' })
  return res.json()
}
""",
    "src/api/ws.ts": """
import { create } from 'zustand'
import { wsEventSchema, lidarStatusSchema } from './schemas'

interface WsState {
  eventsConnected: boolean
  pointsConnected: boolean
  lidarStatuses: Record<string, any>
  connectEvents: () => void
  connectPoints: () => void
}

export const useWsStore = create<WsState>((set, get) => ({
  eventsConnected: false,
  pointsConnected: false,
  lidarStatuses: {},
  
  connectEvents: () => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/events`)
    ws.onopen = () => set({ eventsConnected: true })
    ws.onclose = () => {
      set({ eventsConnected: false })
      setTimeout(get().connectEvents, 1000) // backoff
    }
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        const parsed = wsEventSchema.parse(msg)
        if (parsed.type === 'lidarStatus') {
          const st = lidarStatusSchema.parse(parsed.data)
          set((state) => ({
            lidarStatuses: { ...state.lidarStatuses, [st.id]: st }
          }))
        }
      } catch (err) {
        // ignore
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
""",
    "src/routes/ControlPage.tsx": """
import { useState } from 'react'
import LidarList from '../features/lidar/LidarList'
import TopViewCanvas from '../features/topview/TopViewCanvas'

export default function ControlPage() {
  const [activeTab, setActiveTab] = useState('Lidar')
  const tabs = ['Lidar', 'Input', 'Output', 'Blob', 'Zones', 'Settings']

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 overflow-hidden font-mono">
      <div className="flex-1 relative">
        <TopViewCanvas />
      </div>
      <div className="w-[400px] border-l border-slate-700 bg-slate-800 flex flex-col">
        <div className="flex border-b border-slate-700">
          {tabs.map(t => (
            <button 
              key={t}
              onClick={() => setActiveTab(t)}
              className={`flex-1 py-2 text-xs font-bold ${activeTab === t ? 'bg-slate-700 text-cyan-400' : 'text-slate-400 hover:bg-slate-700'}`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-auto p-4">
          {activeTab === 'Lidar' && <LidarList />}
          {activeTab !== 'Lidar' && <div className="text-slate-500 italic">Empty tab: {activeTab}</div>}
        </div>
      </div>
    </div>
  )
}
""",
    "src/routes/WallPage.tsx": """
export default function WallPage() {
  return (
    <div className="w-screen h-screen bg-black text-white flex items-center justify-center cursor-none">
      <h1 className="text-4xl text-cyan-400 font-bold">Wall View</h1>
    </div>
  )
}
""",
    "src/features/lidar/LidarList.tsx": """
import { useQuery } from '@tanstack/react-query'
import { fetchLidars, connectLidar, disconnectLidar } from '../../api/rest'
import { useWsStore } from '../../api/ws'

export default function LidarList() {
  const { data: lidars, refetch } = useQuery({ queryKey: ['lidars'], queryFn: fetchLidars })
  const statuses = useWsStore(s => s.lidarStatuses)

  const toggle = async (id: string, st: string) => {
    if (st === 'connected') await disconnectLidar(id)
    else await connectLidar(id)
    refetch()
  }

  return (
    <div className="space-y-4">
      {lidars?.map((l: any) => {
        const st = statuses[l.config.id]?.state || l.status.state
        const fps = statuses[l.config.id]?.fps || l.status.fps
        return (
          <div key={l.config.id} className="p-4 bg-slate-700 rounded shadow">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-bold text-lg">{l.config.name}</h3>
              <div className={`w-3 h-3 rounded-full ${st === 'connected' ? 'bg-green-500' : st === 'error' ? 'bg-red-500' : 'bg-yellow-500'}`} />
            </div>
            <div className="text-sm text-slate-300">Model: {l.config.model}</div>
            <div className="text-sm text-slate-300">FPS: {fps.toFixed(1)}</div>
            <button 
              onClick={() => toggle(l.config.id, st)}
              className="mt-2 w-full py-1 bg-slate-600 hover:bg-slate-500 rounded font-bold text-sm"
            >
              {st === 'connected' ? 'Disconnect' : 'Connect'}
            </button>
          </div>
        )
      })}
    </div>
  )
}
""",
    "src/features/topview/TopViewCanvas.tsx": """
import { useEffect, useRef } from 'react'

export default function TopViewCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId: number
    let latestPoints: Float32Array | null = null

    const handlePoints = (e: CustomEvent) => {
      const buffer = e.detail as ArrayBuffer
      if (buffer.byteLength < 16) return
      
      const header = new DataView(buffer)
      const v = header.getUint8(0)
      if (v !== 1) return
      
      const count = header.getUint32(8, true)
      if (buffer.byteLength >= 16 + count * 8) {
        latestPoints = new Float32Array(buffer.slice(16, 16 + count * 8))
      }
    }
    
    window.addEventListener('lidar-points', handlePoints as any)

    const render = () => {
      const w = canvas.width
      const h = canvas.height
      ctx.clearRect(0, 0, w, h)

      // Draw grid / circles
      ctx.save()
      ctx.translate(w/2, h/2) // center is origin (0,0)
      
      // scale: let's say 4m fits in view. 4000mm -> h/2 pixels. scale = h/8000
      const scale = Math.min(w, h) / 8000
      ctx.scale(scale, scale)

      // Draw rings
      ctx.strokeStyle = '#334155'
      ctx.lineWidth = 1/scale
      for (const r of [1000, 2000, 4000]) {
        ctx.beginPath()
        ctx.arc(0, 0, r, 0, 2*Math.PI)
        ctx.stroke()
      }

      // Draw axes
      ctx.lineWidth = 2/scale
      ctx.strokeStyle = '#ef4444' // X red
      ctx.beginPath(); ctx.moveTo(0,0); ctx.lineTo(1000, 0); ctx.stroke()
      ctx.strokeStyle = '#22c55e' // Y green
      ctx.beginPath(); ctx.moveTo(0,0); ctx.lineTo(0, 1000); ctx.stroke()

      // Draw points
      if (latestPoints) {
        ctx.fillStyle = '#f97316' // orange
        for (let i=0; i<latestPoints.length; i+=2) {
          const x = latestPoints[i]
          const y = latestPoints[i+1]
          ctx.fillRect(x - 10, y - 10, 20, 20) // 20mm dot
        }
      }

      ctx.restore()
      animationFrameId = requestAnimationFrame(render)
    }

    render()

    const handleResize = () => {
      const parent = canvas.parentElement
      if (parent) {
        canvas.width = parent.clientWidth * window.devicePixelRatio
        canvas.height = parent.clientHeight * window.devicePixelRatio
        canvas.style.width = `${parent.clientWidth}px`
        canvas.style.height = `${parent.clientHeight}px`
      }
    }
    
    window.addEventListener('resize', handleResize)
    handleResize()

    return () => {
      window.removeEventListener('lidar-points', handlePoints as any)
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return (
    <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
  )
}
""",
    "vite.config.ts": """
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true
      }
    }
  }
})
"""
}

for path, content in files.items():
    full_path = os.path.join("d:/Lidar/Code/lidar-wall-kit/frontend", path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\\n")
