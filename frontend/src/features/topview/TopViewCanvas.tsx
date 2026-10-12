import { useEffect, useRef, useState } from 'react'
import { useWsStore } from '../../api/ws'
import { useUiStore } from '../../stores/uiStore'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, fetchConfig } from '../../api/rest'
import { toCanvas, toMm, hitTestHandle } from '../../utils/geometry'
import { readTopViewTheme } from './theme'

export default function TopViewCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { viewport, setViewport } = useUiStore()
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const queryClient = useQueryClient()
  
  const updateConfig = useMutation({
    mutationFn: (newCfg: any) => api.put('/api/config', newCfg),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  // State for interaction
  const [activeLidarId, setActiveLidarId] = useState<string | null>(null)
  const [editingArea, setEditingArea] = useState<any>(null) // null or copy of quadMm
  const [hoverHandle, setHoverHandle] = useState<number | null>(null)
  
  // Refs for loop
  const pointsRef = useRef<Record<string, Array<{ pts: Float32Array, flags: Uint8Array, ts: number }>>>({})
  const blobsRef = useRef<Record<string, any[]>>({})
  const mouseRef = useRef({ x: 0, y: 0, down: false, dragHandle: -1, lastX: 0, lastY: 0, mode: 'pan' as 'pan' | 'edit' })

  useEffect(() => {
    const handlePoints = (e: CustomEvent) => {
      const buffer = e.detail as ArrayBuffer
      if (buffer.byteLength < 16) return
      
      const header = new DataView(buffer)
      if (header.getUint8(0) !== 1) return
      
      const lidarIdx = header.getUint16(2, true)
      const count = header.getUint32(8, true)
      
      const ptsLen = count * 8
      if (buffer.byteLength >= 16 + ptsLen + count) {
        const pts = new Float32Array(buffer.slice(16, 16 + ptsLen))
        const flags = new Uint8Array(buffer.slice(16 + ptsLen, 16 + ptsLen + count))
        const idxStr = String(lidarIdx)
        if (!pointsRef.current[idxStr]) pointsRef.current[idxStr] = []
        pointsRef.current[idxStr].push({ pts, flags, ts: Date.now() })
        // keep only last 5 frames
        if (pointsRef.current[idxStr].length > 5) pointsRef.current[idxStr].shift()
      }
    }
    
    const handleRawBlobs = (e: CustomEvent) => {
      const { lidarId, blobs } = e.detail
      blobsRef.current[lidarId] = blobs
    }
    
    window.addEventListener('lidar-points', handlePoints as any)
    window.addEventListener('rawBlobs', handleRawBlobs as any)
    return () => {
      window.removeEventListener('lidar-points', handlePoints as any)
      window.removeEventListener('rawBlobs', handleRawBlobs as any)
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId: number
    const dpr = window.devicePixelRatio || 1

    const render = () => {
      const parent = canvas.parentElement
      if (!parent) return
      
      const w = parent.clientWidth
      const h = parent.clientHeight
      
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr
        canvas.height = h * dpr
        canvas.style.width = `${w}px`
        canvas.style.height = `${h}px`
        ctx.scale(dpr, dpr)
      }
      
      ctx.clearRect(0, 0, w, h)
      const theme = readTopViewTheme()
      ctx.fillStyle = theme.canvasBackground
      ctx.fillRect(0, 0, w, h)
      
      const vp = useUiStore.getState().viewport
      const scale = vp.zoom
      
      ctx.save()
      ctx.translate(w/2 + vp.x, h/2 + vp.y)
      
      // Grid
      ctx.strokeStyle = theme.grid
      ctx.lineWidth = 1
      const gridSize = 1000 * scale
      if (gridSize > 5) {
        const startX = - (w/2 + vp.x)
        const startY = - (h/2 + vp.y)
        for (let x = startX - (startX % gridSize); x < startX + w; x += gridSize) {
          ctx.beginPath(); ctx.moveTo(x, startY); ctx.lineTo(x, startY + h); ctx.stroke()
        }
        for (let y = startY - (startY % gridSize); y < startY + h; y += gridSize) {
          ctx.beginPath(); ctx.moveTo(startX, y); ctx.lineTo(startX + w, y); ctx.stroke()
        }
      }
      
      // Axes
      ctx.lineWidth = 2
      ctx.strokeStyle = theme.axisX
      ctx.beginPath(); ctx.moveTo(0,0); ctx.lineTo(1000 * scale, 0); ctx.stroke()
      ctx.strokeStyle = theme.axisY
      ctx.beginPath(); ctx.moveTo(0,0); ctx.lineTo(0, -1000 * scale); ctx.stroke()
      
      // Rings 1m, 2m, 4m
      ctx.strokeStyle = theme.ring
      ctx.lineWidth = 1
      for (const r of [1000, 2000, 4000]) {
        ctx.beginPath()
        ctx.arc(0, 0, r * scale, 0, 2*Math.PI)
        ctx.stroke()
        ctx.fillStyle = theme.ringLabel
        ctx.font = '12px "JetBrains Mono", monospace'
        ctx.fillText(`${r / 1000} m`, 6, -r * scale + 14)
      }
      
      // Lidar Origin Marker
      ctx.beginPath()
      ctx.arc(0, 0, 6, 0, 2*Math.PI)
      ctx.fillStyle = theme.scanArea
      ctx.fill()
      ctx.lineWidth = 2
      ctx.strokeStyle = theme.canvasBackground
      ctx.stroke()
      ctx.fillStyle = theme.ringLabel
      ctx.font = 'bold 12px "JetBrains Mono", monospace'
      ctx.fillText("LIDAR (0,0)", 10, -10)
      
      ctx.restore()
      
      // Points (accumulate frames for density and trail effect)
      const activeLidarIdx = config?.lidars?.findIndex((l: any) => l.id === activeLidarId) ?? -1
      
      for (const [idxStr, frames] of Object.entries(pointsRef.current)) {
        const idx = parseInt(idxStr)
        const isFocus = idx === activeLidarIdx
        
        // Remove old frames
        const validFrames = frames.filter(f => Date.now() - f.ts < 1000)
        pointsRef.current[idxStr] = validFrames
        
        validFrames.forEach((data, frameIdx) => {
          const { pts, flags } = data
          const ageRatio = frameIdx / validFrames.length // 0 is oldest, 1 is newest
          const baseAlpha = 0.3 + 0.7 * ageRatio
          
          let lastX = 0, lastY = 0
          let drawing = false
          
          // Pass 1: Draw points
          for (let i = 0; i < pts.length; i += 2) {
            const x = pts[i]
            const y = pts[i+1]
            const f = flags[i/2]
            
            const isFg = (f & 1) !== 0
            const isIn = (f & 2) !== 0
            
            ctx.globalAlpha = (isFg && isIn ? 1.0 : isFg || isIn ? 0.9 : 0.75) * baseAlpha
            if (isFg) {
              ctx.fillStyle = isFocus ? '#ef4444' : '#f97316'
            } else {
              ctx.fillStyle = isFocus ? '#0284c7' : '#64748b'
            }
            
            const { x: cx, y: cy } = toCanvas(x, y, w, h, vp)
            ctx.fillRect(cx - 2, cy - 2, 4, 4)
          }

          // Pass 2: Draw continuous lines (batched stroke)
          ctx.beginPath()
          drawing = false
          for (let i = 0; i < pts.length; i += 2) {
            const x = pts[i]
            const y = pts[i+1]
            const { x: cx, y: cy } = toCanvas(x, y, w, h, vp)
            
            if (drawing && Math.hypot(x - lastX, y - lastY) < 150) {
              ctx.lineTo(cx, cy)
            } else {
              ctx.moveTo(cx, cy)
            }
            drawing = true
            lastX = x
            lastY = y
          }
          ctx.strokeStyle = isFocus ? 'rgba(2, 132, 199, 0.6)' : 'rgba(100, 116, 139, 0.4)'
          ctx.globalAlpha = 0.7 * baseAlpha
          ctx.lineWidth = 1.5
          ctx.stroke()
        })
        ctx.globalAlpha = 1
      }
      
      // Blobs
      for (const [_, blobs] of Object.entries(blobsRef.current)) {
        for (const b of blobs) {
          const { x: cx, y: cy } = toCanvas(b.x, b.y, w, h, vp)
          const r = Math.max(4, (b.sizeMm / 2) * scale)
          
          ctx.beginPath()
          ctx.arc(cx, cy, r, 0, Math.PI*2)
          ctx.fillStyle = theme.blob
          ctx.globalAlpha = 0.6
          ctx.fill()
          
          ctx.lineWidth = 2
          ctx.strokeStyle = theme.blob
          ctx.globalAlpha = 1
          ctx.stroke()
          
          // Center dot
          ctx.beginPath()
          ctx.arc(cx, cy, 2, 0, Math.PI*2)
          ctx.fillStyle = '#fff'
          ctx.fill()
        }
      }
      
      // Scan Area (Editing or Active)
      if (editingArea) {
        ctx.strokeStyle = theme.scanArea
        ctx.fillStyle = theme.scanFill
        ctx.lineWidth = 2
        
        ctx.beginPath()
        for (let i = 0; i < 4; i++) {
          const { x, y } = toCanvas(editingArea[i][0], editingArea[i][1], w, h, vp)
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.closePath()
        ctx.fill()
        ctx.stroke()
        
        // Handles
        for (let i = 0; i < 4; i++) {
          const { x, y } = toCanvas(editingArea[i][0], editingArea[i][1], w, h, vp)
          const isHover = hoverHandle === i || mouseRef.current.dragHandle === i
          ctx.beginPath()
          ctx.arc(x, y, isHover ? 8 : 6, 0, Math.PI*2)
          ctx.fillStyle = isHover ? theme.scanArea : '#FFFFFF'
          ctx.fill()
          ctx.lineWidth = 2.5
          ctx.strokeStyle = '#000000'
          ctx.stroke()
          ctx.beginPath()
          ctx.arc(x, y, isHover ? 5 : 3.5, 0, Math.PI*2)
          ctx.lineWidth = 1.5
          ctx.strokeStyle = isHover ? '#FFFFFF' : theme.scanArea
          ctx.stroke()
        }
      } else if (config?.lidars) {
        // Draw static scan areas
        for (let i = 0; i < config.lidars.length; i++) {
          const quad = config.lidars[i].scanArea.quadMm
          if (!quad) continue
          
          const isFocus = i === activeLidarIdx
          ctx.strokeStyle = theme.scanArea
          ctx.globalAlpha = isFocus ? 1 : 0.42
          ctx.lineWidth = 2
          
          ctx.beginPath()
          for (let j = 0; j < 4; j++) {
            const { x, y } = toCanvas(quad[j][0], quad[j][1], w, h, vp)
            if (j === 0) ctx.moveTo(x, y)
            else ctx.lineTo(x, y)
          }
          ctx.closePath()
          ctx.stroke()
          ctx.globalAlpha = 1
        }
      }
      
      // Calibration quad
      const calState = useWsStore.getState().calibrationState
      if (calState && calState.state === 'REVIEW' && calState.capturedMm && calState.capturedMm.length >= 4) {
        const pts = calState.capturedMm
        ctx.strokeStyle = theme.wallQuad
        ctx.lineWidth = 2
        ctx.beginPath()
        for (let i=0; i<pts.length; i++) {
          const { x, y } = toCanvas(pts[i][0], pts[i][1], w, h, vp)
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.closePath()
        ctx.stroke()
        
        ctx.fillStyle = theme.wallHandle
        for (let i=0; i<pts.length; i++) {
          const { x, y } = toCanvas(pts[i][0], pts[i][1], w, h, vp)
          ctx.beginPath()
          ctx.arc(x, y, 4, 0, Math.PI*2)
          ctx.fill()
        }
      }

      animationFrameId = requestAnimationFrame(render)
    }
    
    render()
    return () => cancelAnimationFrame(animationFrameId)
  }, [config, activeLidarId, editingArea, hoverHandle])

  // Mouse Handlers

  const handlePointerDown = (e: React.PointerEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    mouseRef.current.down = true
    mouseRef.current.lastX = e.clientX
    mouseRef.current.lastY = e.clientY
    
    if (editingArea) {
      // Hit test handles
      const vp = useUiStore.getState().viewport
      const cx = e.clientX - rect.left
      const cy = e.clientY - rect.top
      
      for (let i = 0; i < 4; i++) {
        const { x: hx, y: hy } = toCanvas(editingArea[i][0], editingArea[i][1], rect.width, rect.height, vp)
        if (hitTestHandle(cx, cy, hx, hy, 15)) {
          mouseRef.current.dragHandle = i
          mouseRef.current.mode = 'edit'
          e.currentTarget.setPointerCapture(e.pointerId)
          return
        }
      }
    }
    mouseRef.current.mode = 'pan'
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  
  const handlePointerMove = (e: React.PointerEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    
    // Hover check
    if (!mouseRef.current.down && editingArea) {
      const vp = useUiStore.getState().viewport
      const cx = e.clientX - rect.left
      const cy = e.clientY - rect.top
      let found = null
      for (let i = 0; i < 4; i++) {
        const { x: hx, y: hy } = toCanvas(editingArea[i][0], editingArea[i][1], rect.width, rect.height, vp)
        if (hitTestHandle(cx, cy, hx, hy, 15)) found = i
      }
      setHoverHandle(found)
    }

    if (!mouseRef.current.down) return
    
    const dx = e.clientX - mouseRef.current.lastX
    const dy = e.clientY - mouseRef.current.lastY
    
    if (mouseRef.current.mode === 'pan') {
      setViewport({ ...viewport, x: viewport.x + dx, y: viewport.y + dy })
    } else if (mouseRef.current.mode === 'edit' && editingArea) {
      const idx = mouseRef.current.dragHandle
      const vp = useUiStore.getState().viewport
      
      // Move corner
      const newArea = [...editingArea]
      // Convert current px to mm difference
      const newCx = (e.clientX - rect.left)
      const newCy = (e.clientY - rect.top)
      const { x: mmX, y: mmY } = toMm(newCx, newCy, rect.width, rect.height, vp)
      newArea[idx] = [mmX, mmY]
      setEditingArea(newArea)
    }
    
    mouseRef.current.lastX = e.clientX
    mouseRef.current.lastY = e.clientY
  }
  
  const handlePointerUp = (e: React.PointerEvent) => {
    mouseRef.current.down = false
    mouseRef.current.dragHandle = -1
    e.currentTarget.releasePointerCapture(e.pointerId)
  }
  
  const handleWheel = (e: React.WheelEvent) => {
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    // Zoom around mouse
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const cx = e.clientX - rect.left
    const cy = e.clientY - rect.top
    
    const { x: curX, y: curY, zoom } = viewport
    
    // Calculate mm coordinate at mouse before zoom
    const w = rect.width
    const h = rect.height
    
    const mouseMmX = (cx - (w/2 + curX)) / zoom
    const mouseMmY = (cy - (h/2 + curY)) / zoom
    
    const newZoom = Math.max(0.01, Math.min(10, zoom * delta))
    
    // Calculate new translation to keep mouse at same mm
    const newX = cx - w/2 - mouseMmX * newZoom
    const newY = cy - h/2 - mouseMmY * newZoom
    
    setViewport({ x: newX, y: newY, zoom: newZoom })
  }

  // UI Actions
  const handleApplyArea = () => {
    if (!activeLidarId || !editingArea || !config) return
    const idx = config.lidars.findIndex((l: any) => l.id === activeLidarId)
    if (idx < 0) return
    
    const newLidars = [...config.lidars]
    newLidars[idx] = { 
      ...newLidars[idx], 
      scanArea: { ...newLidars[idx].scanArea, quadMm: editingArea } 
    }
    
    updateConfig.mutate({ ...config, lidars: newLidars }, {
      onSuccess: () => setEditingArea(null)
    })
  }

  const cursorClass = editingArea 
    ? (hoverHandle !== null ? 'cursor-move' : 'cursor-default') 
    : (mouseRef.current.down ? 'cursor-grabbing' : 'cursor-grab')

  return (
    <div className="absolute inset-0 overflow-hidden bg-navy-950 lidar-display-area">
      <canvas 
        ref={canvasRef} 
        className={`absolute inset-0 w-full h-full lidar-canvas ${cursorClass}`}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
      />
      
      {/* Top HUD */}
      <div className="absolute top-4 left-4 flex items-center space-x-2 z-10">
        <select 
          value={activeLidarId || ''} 
          onChange={e => setActiveLidarId(e.target.value)}
          className="input-neon bg-navy-900/80 backdrop-blur"
        >
          <option value="">-- All Lidars --</option>
          {config?.lidars?.map((l: any) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        
        {activeLidarId && !editingArea && (
          <button 
            onClick={() => {
              const l = config?.lidars?.find((x: any) => x.id === activeLidarId)
              if (l) setEditingArea([...l.scanArea.quadMm])
            }} 
            className="btn-neon bg-navy-900/80 backdrop-blur"
          >
            Edit Area
          </button>
        )}
        
        {editingArea && (
          <>
            <button onClick={handleApplyArea} className="btn-neon border-green-500 text-green-400 hover:bg-green-500/20 bg-navy-900/80 backdrop-blur">Apply</button>
            <button onClick={() => setEditingArea(null)} className="btn-neon-danger bg-navy-900/80 backdrop-blur">Cancel</button>
          </>
        )}
      </div>
      
      {/* Viewport controls */}
      <div className="absolute bottom-4 left-4 flex flex-col space-y-2 z-10">
        <button onClick={() => setViewport({ ...viewport, zoom: viewport.zoom * 1.2 })} className="btn-neon !px-2 bg-navy-900/80">+</button>
        <button onClick={() => setViewport({ ...viewport, zoom: viewport.zoom / 1.2 })} className="btn-neon !px-2 bg-navy-900/80">-</button>
        <button onClick={() => setViewport({ x: 0, y: 0, zoom: 0.2 })} className="btn-neon !px-2 bg-navy-900/80">R</button>
      </div>
    </div>
  )
}
