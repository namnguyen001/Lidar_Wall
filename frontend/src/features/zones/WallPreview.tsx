import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, fetchConfig } from '../../api/rest'
import { readTopViewTheme } from '../topview/theme'

export default function WallPreview({ activeZone, mode = 'zone', activeLidarId }: { activeZone?: any, mode?: 'zone' | 'coverage', activeLidarId?: string | null }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  
  const queryClient = useQueryClient()
  const updateConfig = useMutation({
    mutationFn: (newCfg: any) => api.put('/api/config', newCfg),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  const [editingQuad, setEditingQuad] = useState<any>(null)
  const [dragState, setDragState] = useState({ handle: -1, isDragging: false })
  
  useEffect(() => {
    if (mode === 'coverage' && activeLidarId && config) {
      const l = config.lidars.find((x: any) => x.id === activeLidarId)
      if (l) setEditingQuad([...l.coverageUv])
    } else {
      setEditingQuad(null)
    }
  }, [mode, activeLidarId, config])
  
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !config) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    
    let animationFrameId: number
    
    const render = () => {
      const w = canvas.width
      const h = canvas.height
      const theme = readTopViewTheme()
      ctx.clearRect(0, 0, w, h)
      ctx.fillStyle = theme.canvasBackground
      ctx.fillRect(0, 0, w, h)
      
      // Draw zones if mode is zone
      if (mode === 'zone') {
        const zones = config.zones || []
        const sortedZones = [...zones].sort((a, b) => a.layer - b.layer)
        
        for (const z of sortedZones) {
          if (!z.enabled && z.id !== activeZone?.id) continue
          
          ctx.fillStyle = z.color + (z.id === activeZone?.id ? '80' : '40') // hex alpha
          ctx.strokeStyle = z.color
          ctx.lineWidth = z.id === activeZone?.id ? 4 : 2
          
          ctx.beginPath()
          if (z.shape.type === 'rect') {
            ctx.rect(z.shape.x * w, z.shape.y * h, z.shape.w * w, z.shape.h * h)
          } else if (z.shape.type === 'circle') {
            ctx.arc(z.shape.cx * w, z.shape.cy * h, z.shape.r * w, 0, Math.PI * 2)
          } else if (z.shape.type === 'polygon') {
            const pts = z.shape.points
            if (pts && pts.length >= 3) {
              ctx.moveTo(pts[0][0] * w, pts[0][1] * h)
              for (let i = 1; i < pts.length; i++) {
                ctx.lineTo(pts[i][0] * w, pts[i][1] * h)
              }
              ctx.closePath()
            }
          }
          ctx.fill()
          ctx.stroke()
          
          // Draw handles if active
          if (z.id === activeZone?.id) {
            ctx.fillStyle = theme.canvasBackground
            ctx.strokeStyle = theme.hudText
            ctx.lineWidth = 1
            
            const drawHandle = (hx: number, hy: number) => {
              ctx.beginPath()
              ctx.arc(hx * w, hy * h, 7, 0, Math.PI * 2)
              ctx.fillStyle = '#FFFFFF'
              ctx.fill()
              ctx.lineWidth = 2.5
              ctx.strokeStyle = '#000000'
              ctx.stroke()
              ctx.beginPath()
              ctx.arc(hx * w, hy * h, 4, 0, Math.PI * 2)
              ctx.fillStyle = theme.hudText
              ctx.fill()
            }
            
            if (z.shape.type === 'rect') {
              drawHandle(z.shape.x, z.shape.y)
              drawHandle(z.shape.x + z.shape.w, z.shape.y + z.shape.h)
            } else if (z.shape.type === 'circle') {
              drawHandle(z.shape.cx, z.shape.cy)
              drawHandle(z.shape.cx + z.shape.r, z.shape.cy)
            } else if (z.shape.type === 'polygon') {
              z.shape.points.forEach((p: any) => drawHandle(p[0], p[1]))
            }
          }
        }
      }
      
      // Draw coverage as background context for zone mode, or active for coverage mode
      const lidars = config.lidars || []
      const colors = [theme.scanArea, theme.wallHandle, theme.wallQuad, theme.axisY]
      
      for (let i = 0; i < lidars.length; i++) {
        const l = lidars[i]
        if (!l.enabled) continue
        
        const isActive = mode === 'coverage' && l.id === activeLidarId
        const quad = l.coverageUv
        if (!quad) continue
        
        const color = colors[i % colors.length]
        ctx.fillStyle = color + (isActive ? '60' : '10') // Very faint if in zone mode
        ctx.strokeStyle = color + (mode === 'zone' ? '40' : '') // Faint border in zone mode
        ctx.lineWidth = isActive ? 4 : (mode === 'zone' ? 1 : 2)
        
        ctx.beginPath()
        ctx.moveTo(quad[0][0] * w, quad[0][1] * h)
        for (let j = 1; j < 4; j++) {
          ctx.lineTo(quad[j][0] * w, quad[j][1] * h)
        }
        ctx.closePath()
        ctx.fill()
        ctx.stroke()
        
        if (isActive) {
          for (let j = 0; j < 4; j++) {
            const isHover = dragState.handle === j
            ctx.beginPath()
            ctx.arc(quad[j][0] * w, quad[j][1] * h, isHover ? 9 : 7, 0, Math.PI * 2)
            ctx.fillStyle = isHover ? color : '#FFFFFF'
            ctx.fill()
            ctx.lineWidth = 2.5
            ctx.strokeStyle = '#000000'
            ctx.stroke()
            ctx.beginPath()
            ctx.arc(quad[j][0] * w, quad[j][1] * h, isHover ? 6 : 4, 0, Math.PI * 2)
            ctx.lineWidth = 1.5
            ctx.strokeStyle = isHover ? '#FFFFFF' : color
            ctx.stroke()
          }
        }
      }
      
      // Draw live Blobs
      const blobs = Array.isArray(blobsRef.current) ? blobsRef.current : []
      ctx.fillStyle = theme.blob
      for (const b of blobs) {
        ctx.beginPath()
        ctx.arc(b.x * w, b.y * h, 10, 0, Math.PI * 2)
        ctx.globalAlpha = 0.5
        ctx.fill()
        ctx.globalAlpha = 1
        ctx.lineWidth = 2
        ctx.strokeStyle = theme.blob
        ctx.stroke()
        ctx.beginPath()
        ctx.arc(b.x * w, b.y * h, 2, 0, Math.PI * 2)
        ctx.fillStyle = '#fff'
        ctx.fill()
      }

      animationFrameId = requestAnimationFrame(render)
    }
    
    render()
    
    const handleResize = () => {
      const parent = canvas.parentElement
      if (parent) {
        // Enforce wall aspect ratio
        const wallW = config.wall.widthPx
        const wallH = config.wall.heightPx
        const aspect = wallW / wallH
        
        let cw = parent.clientWidth
        let ch = cw / aspect
        if (ch > parent.clientHeight) {
          ch = parent.clientHeight
          cw = ch * aspect
        }
        
        canvas.width = cw * window.devicePixelRatio
        canvas.height = ch * window.devicePixelRatio
        canvas.style.width = `${cw}px`
        canvas.style.height = `${ch}px`
      }
    }
    
    window.addEventListener('resize', handleResize)
    handleResize()
    
    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameId)
    }
  }, [config, activeZone, mode, activeLidarId, editingQuad])
  
  // Add blob ref
  const blobsRef = useRef<any[]>([])
  useEffect(() => {
    const handleBlobs = (e: CustomEvent) => {
      const raw = e.detail as any
      blobsRef.current = Array.isArray(raw) ? raw : (Array.isArray(raw?.blobs) ? raw.blobs : [])
    }
    window.addEventListener('blobs', handleBlobs as any)
    return () => window.removeEventListener('blobs', handleBlobs as any)
  }, [])

  const handlePointerDown = (e: React.PointerEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const cx = (e.clientX - rect.left) / rect.width
    const cy = (e.clientY - rect.top) / rect.height
    
    if (mode === 'coverage' && editingQuad) {
      for (let i = 0; i < 4; i++) {
        const hx = editingQuad[i][0]
        const hy = editingQuad[i][1]
        const dx = (cx - hx) * rect.width
        const dy = (cy - hy) * rect.height
        if (Math.hypot(dx, dy) < 15) {
          setDragState({ handle: i, isDragging: true })
          e.currentTarget.setPointerCapture(e.pointerId)
          return
        }
      }
    } else if (mode === 'zone' && activeZone) {
      // Find active zone handle
      const z = config?.zones?.find((x:any) => x.id === activeZone.id)
      if (!z) return
      
      const checkHandle = (hx: number, hy: number, id: number) => {
        const dx = (cx - hx) * rect.width
        const dy = (cy - hy) * rect.height
        if (Math.hypot(dx, dy) < 15) {
          setDragState({ handle: id, isDragging: true })
          e.currentTarget.setPointerCapture(e.pointerId)
          return true
        }
        return false
      }
      
      if (z.shape.type === 'rect') {
        if (checkHandle(z.shape.x, z.shape.y, 0)) return // top-left
        if (checkHandle(z.shape.x + z.shape.w, z.shape.y + z.shape.h, 1)) return // bottom-right
      } else if (z.shape.type === 'circle') {
        if (checkHandle(z.shape.cx, z.shape.cy, 0)) return // center
        if (checkHandle(z.shape.cx + z.shape.r, z.shape.cy, 1)) return // edge
      } else if (z.shape.type === 'polygon') {
        for (let i = 0; i < z.shape.points.length; i++) {
          if (checkHandle(z.shape.points[i][0], z.shape.points[i][1], i)) return
        }
      }
    }
  }
  
  const handlePointerMove = (e: React.PointerEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const cx = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const cy = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height))
    
    if (!dragState.isDragging) {
      // Hover logic
      let hoverId = -1
      if (mode === 'coverage' && editingQuad) {
        for (let i = 0; i < 4; i++) {
          if (Math.hypot((cx - editingQuad[i][0]) * rect.width, (cy - editingQuad[i][1]) * rect.height) < 15) {
            hoverId = i; break;
          }
        }
      } else if (mode === 'zone' && activeZone && config) {
        const z = config.zones.find((x:any) => x.id === activeZone.id)
        if (z) {
          const check = (hx: number, hy: number, id: number) => {
            if (Math.hypot((cx - hx) * rect.width, (cy - hy) * rect.height) < 15) { hoverId = id; return true; }
            return false;
          }
          if (z.shape.type === 'rect') {
            check(z.shape.x, z.shape.y, 0) || check(z.shape.x + z.shape.w, z.shape.y + z.shape.h, 1)
          } else if (z.shape.type === 'circle') {
            check(z.shape.cx, z.shape.cy, 0) || check(z.shape.cx + z.shape.r, z.shape.cy, 1)
          } else if (z.shape.type === 'polygon') {
            z.shape.points.some((p:any, i:number) => check(p[0], p[1], i))
          }
        }
      }
      if (dragState.handle !== hoverId) setDragState({ ...dragState, handle: hoverId })
      return
    }
    
    if (dragState.handle < 0) return
    
    if (mode === 'coverage' && editingQuad) {
      const newQuad = [...editingQuad]
      newQuad[dragState.handle] = [cx, cy]
      setEditingQuad(newQuad)
    } else if (mode === 'zone' && activeZone && config) {
      const idx = config.zones.findIndex((x:any) => x.id === activeZone.id)
      if (idx < 0) return
      const newZones = [...config.zones]
      const z = { ...newZones[idx], shape: { ...newZones[idx].shape } }
      
      if (z.shape.type === 'rect') {
        if (dragState.handle === 0) {
          const right = z.shape.x + z.shape.w
          const bottom = z.shape.y + z.shape.h
          z.shape.x = Math.min(cx, right - 0.01)
          z.shape.y = Math.min(cy, bottom - 0.01)
          z.shape.w = right - z.shape.x
          z.shape.h = bottom - z.shape.y
        } else {
          z.shape.w = Math.max(0.01, cx - z.shape.x)
          z.shape.h = Math.max(0.01, cy - z.shape.y)
        }
      } else if (z.shape.type === 'circle') {
        if (dragState.handle === 0) {
          z.shape.cx = cx
          z.shape.cy = cy
        } else {
          z.shape.r = Math.hypot(cx - z.shape.cx, cy - z.shape.cy)
        }
      } else if (z.shape.type === 'polygon') {
        const pts = [...z.shape.points]
        pts[dragState.handle] = [cx, cy]
        z.shape.points = pts
      }
      
      newZones[idx] = z
      queryClient.setQueryData(['config'], { ...config, zones: newZones })
    }
  }
  
  const handlePointerUp = (e: React.PointerEvent) => {
    if (dragState.isDragging && config) {
      if (mode === 'coverage' && editingQuad && activeLidarId) {
        const idx = config.lidars.findIndex((l: any) => l.id === activeLidarId)
        if (idx >= 0) {
          const newLidars = [...config.lidars]
          newLidars[idx] = { ...newLidars[idx], coverageUv: editingQuad }
          updateConfig.mutate({ ...config, lidars: newLidars })
        }
      } else if (mode === 'zone' && activeZone) {
        updateConfig.mutate(config) // Save the optimistic update
      }
    }
    setDragState({ handle: -1, isDragging: false })
    e.currentTarget.releasePointerCapture(e.pointerId)
  }
  
  let cursorClass = 'cursor-default'
  if (mode === 'coverage' || mode === 'zone') {
    if (dragState.isDragging) cursorClass = 'cursor-move'
    else if (dragState.handle >= 0) cursorClass = 'cursor-move'
  }

  return (
    <div className="absolute inset-0 flex items-center justify-center bg-navy-950 lidar-display-area" onPointerMove={handlePointerMove}>
      <canvas 
        ref={canvasRef} 
        className={`bg-navy-900 border border-navy-700 shadow-2xl lidar-canvas ${cursorClass}`}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      />
    </div>
  )
}
