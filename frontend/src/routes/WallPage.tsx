import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWsStore } from '../api/ws'
import { api, fetchConfig } from '../api/rest'

// Safe default points placed with generous margin away from screen edges & HUD
const DEFAULT_TARGETS: Array<[number, number]> = [
  [0.20, 0.25], // 1: Top-Left (below top HUD)
  [0.80, 0.25], // 2: Top-Right
  [0.80, 0.75], // 3: Bottom-Right (above bottom edge)
  [0.20, 0.75], // 4: Bottom-Left
]

const TARGET_NAMES = [
  'Góc Trên-Trái (1)',
  'Góc Trên-Phải (2)',
  'Góc Dưới-Phải (3)',
  'Góc Dưới-Trái (4)',
]

function safeInsetTargets(pts: Array<[number, number]>): Array<[number, number]> {
  return pts.map(([u, v]) => {
    const safeU = Math.max(0.08, Math.min(0.92, u <= 0.05 ? 0.18 : (u >= 0.95 ? 0.82 : u)))
    const safeV = Math.max(0.18, Math.min(0.84, v <= 0.05 ? 0.25 : (v >= 0.95 ? 0.75 : v)))
    return [Number(safeU.toFixed(3)), Number(safeV.toFixed(3))]
  })
}

export default function WallPage() {
  const navigate = useNavigate()
  const calState = useWsStore((s) => s.calibrationState)
  const [blobs, setBlobs] = useState<any[]>([])
  const [testMode, setTestMode] = useState(true) // Default to TRUE so user can test immediately!
  const [showZones, setShowZones] = useState(false)
  const [showTargetGuides, setShowTargetGuides] = useState(false)
  const [successToast, setSuccessToast] = useState<string | null>(null)
  const [config, setConfig] = useState<any>(null)
  const [zoneStates, setZoneStates] = useState<Record<string, any>>({})

  // In-wall calibration state
  const [selectedLidarId, setSelectedLidarId] = useState<string>('')
  const [editableTargets, setEditableTargets] = useState<Array<[number, number]>>(DEFAULT_TARGETS)
  const [draggingIdx, setDraggingIdx] = useState<number | null>(null)
  const [hudVisible, setHudVisible] = useState(true)

  // Load config & initialize selected lidar & targets safely
  useEffect(() => {
    fetchConfig()
      .then((cfg) => {
        setConfig(cfg)
        if (cfg?.lidars?.length > 0) {
          const first = cfg.lidars.find((l: any) => l.enabled) || cfg.lidars[0]
          setSelectedLidarId((prev) => prev || first.id)
          if (first?.coverageUv && first.coverageUv.length === 4) {
            setEditableTargets(safeInsetTargets(first.coverageUv.map((pt: any) => [pt[0], pt[1]])))
          }
          // If not calibrated yet, show target guides to help setup; otherwise start in test mode!
          if (!first?.calibration?.homography) {
            setShowTargetGuides(true)
          }
        }
      })
      .catch(console.error)
  }, [])

  // Update targets when user changes selected lidar
  const handleSelectLidar = (lidarId: string) => {
    setSelectedLidarId(lidarId)
    if (!config?.lidars) return
    const l = config.lidars.find((x: any) => x.id === lidarId)
    if (l?.coverageUv && l.coverageUv.length === 4) {
      setEditableTargets(safeInsetTargets(l.coverageUv.map((pt: any) => [pt[0], pt[1]])))
    } else {
      setEditableTargets(DEFAULT_TARGETS)
    }
  }

  const exitWall = async () => {
    // 1. Direct pywebview call if available
    if (window.pywebview?.api?.close_wall) {
      try {
        await window.pywebview.api.close_wall()
        return
      } catch {}
    }

    // 2. Exit fullscreen if active
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {})
    }

    // 3. Try window.close()
    try {
      window.close()
    } catch {}

    // 4. Fallback navigation if regular browser tab
    if (!window.pywebview && window.location.pathname === '/wall') {
      navigate('/control')
    }
  }

  // Key handlers
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'f' || e.key === 'F') {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {})
        } else {
          document.exitFullscreen().catch(() => {})
        }
      }

      if (e.key === 'd' || e.key === 'D') {
        setShowZones((prev) => !prev)
      }

      if (e.key === 't' || e.key === 'T') {
        setTestMode((prev) => !prev)
      }

      if (e.key === 'h' || e.key === 'H') {
        setHudVisible((prev) => !prev)
      }

      if (e.key === 'Escape') {
        if (calState && ['WAIT_HAND', 'CAPTURING'].includes(calState.state)) {
          api.post('/api/calibration/cancel', {}).catch(console.error)
        }
        exitWall()
        return
      }

      if (calState && ['WAIT_HAND', 'CAPTURING'].includes(calState.state)) {
        if (e.code === 'Space') {
          api.post('/api/calibration/capture', {}).catch(console.error)
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [calState])

  useEffect(() => {
    document.documentElement.dataset.theme = config?.ui?.wallTheme === 'light' ? 'light' : 'dark'
  }, [config?.ui?.wallTheme])

  useEffect(() => {
    const onBlobs = (e: any) => {
      const data = e.detail
      const list = Array.isArray(data) ? data : Array.isArray(data?.blobs) ? data.blobs : []
      setBlobs(list)
    }
    const onZoneState = (e: any) => {
      const zState = e.detail
      setZoneStates((prev) => ({ ...prev, [zState.zoneId]: zState }))
    }
    window.addEventListener('blobs', onBlobs)
    window.addEventListener('zoneState', onZoneState)
    return () => {
      window.removeEventListener('blobs', onBlobs)
      window.removeEventListener('zoneState', onZoneState)
    }
  }, [])

  // Start in-wall calibration
  const startCal = async () => {
    if (!selectedLidarId) return
    setShowTargetGuides(true)
    try {
      await api.post('/api/calibration/start', {
        lidarId: selectedLidarId,
        targetsUv: editableTargets,
        samplesPerPoint: 40,
      })
    } catch (err) {
      console.error('Failed to start calibration:', err)
    }
  }

  const cancelCal = () => api.post('/api/calibration/cancel', {}).catch(console.error)
  const commitCal = async () => {
    try {
      const res = await api.post('/api/calibration/commit', {})
      if (res.data) {
        useWsStore.setState({ calibrationState: res.data })
      }
      setShowTargetGuides(false)
      setTestMode(true)
      setSuccessToast('✓ Hiệu chuẩn thành công! Hãy bước chân vào sàn để test tương tác.')
      setTimeout(() => setSuccessToast(null), 6000)
      fetchConfig().then(setConfig).catch(console.error)
    } catch (err: any) {
      console.error('Failed to commit calibration:', err)
      const msg = err?.response?.data?.detail || err?.message || 'Lỗi không xác định'
      alert(`Không thể lưu cấu hình: ${msg}`)
    }
  }
  const captureCal = () => api.post('/api/calibration/capture', {}).catch(console.error)

  const resetTargets = () => {
    setEditableTargets(DEFAULT_TARGETS)
  }

  // Scale target points inward or outward comfortably
  const scaleTargets = (factor: number) => {
    setEditableTargets((prev) => {
      const cx = 0.5
      const cy = 0.5
      return prev.map(([u, v]) => {
        const nu = Math.max(0.08, Math.min(0.92, cx + (u - cx) * factor))
        const nv = Math.max(0.18, Math.min(0.84, cy + (v - cy) * factor))
        return [Number(nu.toFixed(3)), Number(nv.toFixed(3))]
      })
    })
  }

  // Pointer dragging for the 4 target points
  const handleTargetPointerDown = (idx: number, e: React.PointerEvent) => {
    if (calState && ['WAIT_HAND', 'CAPTURING'].includes(calState.state)) return
    e.stopPropagation()
    e.preventDefault()
    setDraggingIdx(idx)
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }

  const handlePointerMove = (e: React.PointerEvent) => {
    if (draggingIdx === null) return
    // Allow dragging freely across the whole floor screen, with small safe margins
    const u = Math.max(0.04, Math.min(0.96, e.clientX / window.innerWidth))
    const v = Math.max(0.14, Math.min(0.88, e.clientY / window.innerHeight))
    setEditableTargets((prev) => {
      const next = [...prev] as Array<[number, number]>
      next[draggingIdx] = [Number(u.toFixed(3)), Number(v.toFixed(3))]
      return next
    })
  }

  const handlePointerUp = (e: React.PointerEvent) => {
    if (draggingIdx !== null) {
      try {
        ;(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId)
      } catch {}
      setDraggingIdx(null)
    }
  }

  const isCalibrating = calState && ['WAIT_HAND', 'CAPTURING'].includes(calState.state)
  const isReview = calState && calState.state === 'REVIEW'

  // Current targets to render (from calState if calibrating, else editableTargets)
  const activeTargets: Array<[number, number]> =
    isCalibrating && calState?.targetsUv?.length === 4 ? calState.targetsUv : editableTargets

  return (
    <div
      data-testid="wall-page"
      className="w-screen h-screen bg-navy-950 overflow-hidden relative cursor-default select-none"
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      {/* Grid background */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSA0MCAwIEwgMCAwIDAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzIyMiIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-20" />

      {/* FLOATING IN-WALL CONTROL HUD BAR */}
      {hudVisible && (
        <div className="absolute top-3 inset-x-6 z-50 flex flex-wrap items-center justify-between gap-3 bg-navy-900/95 border border-cyan-500/40 backdrop-blur-md px-5 py-3 rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.8)]">
          {/* Left: LiDAR select & Calibrate actions */}
          <div className="flex items-center flex-wrap gap-2.5">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">LiDAR:</span>
            <select
              value={selectedLidarId}
              onChange={(e) => handleSelectLidar(e.target.value)}
              disabled={Boolean(isCalibrating)}
              className="bg-navy-950 text-cyan-300 font-bold text-sm px-3 py-1.5 rounded-lg border border-navy-600 focus:border-neon-cyan focus:outline-none"
            >
              {config?.lidars?.map((l: any) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.model}) {l.enabled ? '●' : '○'}
                </option>
              ))}
            </select>

            {!isCalibrating && !isReview && (
              <>
                <button
                  onClick={() => setShowTargetGuides((v) => !v)}
                  className={`px-3.5 py-1.5 text-xs font-bold rounded-lg border transition shadow-sm ${
                    showTargetGuides
                      ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300'
                      : 'bg-navy-800 hover:bg-navy-700 border-navy-600 text-slate-300'
                  }`}
                  title="Bật/tắt 4 điểm mục tiêu để căn chỉnh góc chiếu"
                >
                  {showTargetGuides ? '✕ Ẩn 4 góc' : '🎯 Căn 4 góc'}
                </button>

                <button
                  onClick={startCal}
                  className="px-4 py-1.5 bg-gradient-to-r from-cyan-500 to-teal-400 hover:brightness-110 text-navy-950 font-extrabold text-xs rounded-lg shadow-[0_0_20px_rgba(6,182,212,0.6)] transition active:scale-95"
                >
                  ▶ Calibrate 4 điểm
                </button>

                {showTargetGuides && (
                  <div className="flex items-center gap-1 bg-navy-950 px-2 py-1 rounded-lg border border-navy-700">
                    <span className="text-[11px] text-slate-400 font-bold px-1">Căn khung:</span>
                    <button
                      onClick={() => scaleTargets(1.15)}
                      className="px-2 py-0.5 bg-navy-800 hover:bg-navy-700 text-cyan-300 font-bold text-xs rounded border border-navy-600 transition"
                      title="Mở rộng 4 điểm ra xa"
                    >
                      + Rộng
                    </button>
                    <button
                      onClick={() => scaleTargets(0.85)}
                      className="px-2 py-0.5 bg-navy-800 hover:bg-navy-700 text-cyan-300 font-bold text-xs rounded border border-navy-600 transition"
                      title="Thu hẹp 4 điểm vào trong"
                    >
                      - Thu
                    </button>
                    <button
                      onClick={resetTargets}
                      className="px-2 py-0.5 bg-navy-800 hover:bg-navy-700 text-slate-300 text-xs rounded border border-navy-600 transition"
                      title="Đặt lại vị trí chuẩn"
                    >
                      ↺ Mặc định
                    </button>
                  </div>
                )}
              </>
            )}

            {isCalibrating && (
              <>
                <div className="flex items-center gap-3 bg-navy-900/90 border border-orange-500/40 px-3.5 py-1 rounded-xl shadow-lg backdrop-blur-md">
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-orange-400">
                      🎯 Điểm {calState.pointIndex + 1}/{calState.pointCount}: {TARGET_NAMES[calState.pointIndex] || ''}
                    </span>
                    <div className="w-32 h-1.5 bg-navy-950 rounded-full overflow-hidden mt-1 border border-orange-500/30">
                      <div
                        className="h-full bg-gradient-to-r from-orange-500 via-amber-400 to-green-400 transition-all duration-150"
                        style={{ width: `${calState.progressPct || 0}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold text-amber-300">
                    {calState.progressPct || 0}%
                  </span>
                </div>

                <button
                  onClick={captureCal}
                  disabled={(calState.progressPct || 0) < 30 && calState.samples < 10}
                  className={`px-4 py-1.5 font-bold text-xs rounded-lg shadow-md transition flex items-center gap-1.5 ${
                    (calState.progressPct || 0) >= 30 || calState.samples >= 10
                      ? 'bg-green-600 hover:bg-green-500 text-white cursor-pointer active:scale-95 shadow-[0_0_15px_rgba(34,197,94,0.5)]'
                      : 'bg-navy-800 text-slate-500 cursor-not-allowed border border-navy-700'
                  }`}
                  title={
                    (calState.progressPct || 0) >= 30
                      ? 'Chốt điểm này'
                      : 'Đang đợi lấy mẫu ổn định (đạt ít nhất 30%)'
                  }
                >
                  ⎵ Chốt điểm (Space)
                </button>
                <button
                  onClick={cancelCal}
                  className="px-3 py-1.5 bg-red-600/90 hover:bg-red-500 text-white font-bold text-xs rounded-lg shadow-md transition"
                >
                  ✕ Hủy
                </button>
              </>
            )}

            {isReview && (
              <>
                <span
                  className={`text-sm font-bold px-3 py-1.5 rounded-lg ${
                    calState.result?.ok
                      ? 'bg-green-500/20 text-green-400 border border-green-500/40'
                      : 'bg-red-500/20 text-red-400 border border-red-500/40'
                  }`}
                >
                  RMS: {calState.result?.rmsPx.toFixed(1)} px
                </span>
                <button
                  onClick={commitCal}
                  className="px-5 py-2 bg-green-500 hover:bg-green-400 text-navy-950 font-bold text-sm rounded-lg shadow-[0_0_20px_rgba(34,197,94,0.6)] transition"
                >
                  ✓ LƯU (Commit)
                </button>
                <button
                  onClick={startCal}
                  className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs rounded-lg transition"
                >
                  ↺ Làm lại
                </button>
              </>
            )}
          </div>

          {/* Right: Quick toggles & Exit */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTestMode((v) => !v)}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition ${
                testMode
                  ? 'bg-yellow-500/20 border-yellow-500 text-yellow-300'
                  : 'bg-navy-800 border-navy-700 text-slate-400'
              }`}
              title="Phím T để bật/tắt"
            >
              Test [T]
            </button>
            <button
              onClick={() => setShowZones((v) => !v)}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition ${
                showZones
                  ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                  : 'bg-navy-800 border-navy-700 text-slate-400'
              }`}
              title="Phím D để bật/tắt"
            >
              Zones [D]
            </button>
            <button
              onClick={() => {
                if (!document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {})
                else document.exitFullscreen().catch(() => {})
              }}
              className="px-3 py-1.5 text-xs font-bold rounded-lg border bg-navy-800 border-navy-700 text-slate-300 hover:text-white transition"
              title="Phím F để bật/tắt"
            >
              Full [F]
            </button>
            <button
              onClick={exitWall}
              className="px-3.5 py-1.5 bg-red-600/90 hover:bg-red-500 text-white font-bold text-xs rounded-lg transition shadow-md"
              title="Phím ESC để thoát"
            >
              ✕ Thoát [ESC]
            </button>
          </div>
        </div>
      )}

      {/* Toggle HUD icon when collapsed */}
      {!hudVisible && (
        <button
          onClick={() => setHudVisible(true)}
          className="absolute top-4 right-4 z-50 px-4 py-2 bg-navy-900/90 border border-cyan-500 text-cyan-400 text-sm font-bold rounded-xl hover:bg-navy-800 transition shadow-xl"
        >
          ⚙ Menu [H]
        </button>
      )}

      {/* Success Toast Banner */}
      {successToast && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 z-50 pointer-events-none">
          <div className="bg-emerald-500/90 text-navy-950 font-black px-6 py-3 rounded-2xl shadow-[0_0_40px_rgba(16,185,129,0.8)] backdrop-blur-md text-base border-2 border-emerald-300 animate-bounce">
            {successToast}
          </div>
        </div>
      )}

      {/* Polygon & 4 Target Circles (Only shown when Calibrating or in Setup Mode) */}
      {(isCalibrating || showTargetGuides) && (
        <>
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
            <polygon
              points={activeTargets.map((p) => `${p[0] * 100}%,${p[1] * 100}%`).join(' ')}
              stroke={isCalibrating ? 'rgba(6,182,212,0.8)' : 'rgba(249,115,22,0.7)'}
              strokeWidth="3"
              strokeDasharray={isCalibrating ? '10,10' : 'none'}
              fill={isCalibrating ? 'rgba(6,182,212,0.08)' : 'rgba(249,115,22,0.06)'}
            />
          </svg>

          {/* Guide text when in Setup/Editable mode */}
          {!isCalibrating && !isReview && (
            <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-30 pointer-events-none text-center">
              <div className="inline-block bg-navy-900/95 border border-cyan-500/50 px-6 py-2.5 rounded-full text-cyan-300 text-sm shadow-2xl backdrop-blur-md">
                ✦ Dùng chuột kéo 4 điểm mục tiêu (hoặc bấm <strong>"+ Rộng / - Thu"</strong> ở trên) ➔ Bấm <strong>"▶ Calibrate 4 điểm"</strong>
              </div>
            </div>
          )}

          {/* 4 TARGET CIRCLES */}
          <div className="absolute inset-0 z-30 pointer-events-none">
            {activeTargets.map((t, i) => {
              const isCurrent = isCalibrating && i === calState?.pointIndex
              const isDone = isCalibrating && (i < calState?.pointIndex || (calState?.savedPoints || []).includes(i))
              const canDrag = !isCalibrating && !isReview
              const progress = isCurrent ? (calState?.progressPct || 0) : isDone ? 100 : 0

              const r = 44
              const circ = 2 * Math.PI * r
              const strokeDashoffset = circ - (progress / 100) * circ

              return (
                <div
                  key={i}
                  onPointerDown={(e) => canDrag && handleTargetPointerDown(i, e)}
                  className={`absolute w-24 h-24 -ml-12 -mt-12 rounded-full flex flex-col items-center justify-center transition-all duration-200 select-none ${
                    canDrag
                      ? 'pointer-events-auto cursor-grab active:cursor-grabbing hover:scale-110 shadow-[0_0_30px_rgba(6,182,212,0.7)] border-4 border-cyan-400 bg-cyan-500/20'
                      : ''
                  } ${
                    isDone
                      ? 'border-4 border-green-400 bg-green-500/30 shadow-[0_0_35px_rgba(34,197,94,0.8)] scale-110'
                      : isCurrent
                      ? 'shadow-[0_0_50px_rgba(249,115,22,0.9)] scale-125'
                      : !canDrag
                      ? 'border-4 border-slate-700/80 bg-navy-950/60 opacity-60'
                      : ''
                  }`}
                  style={{ left: `${t[0] * 100}%`, top: `${t[1] * 100}%` }}
                >
                  {/* Circular SVG Progress Ring for Active Point */}
                  {isCurrent && (
                    <svg className="absolute -inset-2 w-28 h-28 -rotate-90 pointer-events-none">
                      <circle
                        cx="56"
                        cy="56"
                        r={r}
                        stroke="rgba(255,255,255,0.15)"
                        strokeWidth="6"
                        fill="none"
                      />
                      <circle
                        cx="56"
                        cy="56"
                        r={r}
                        stroke={progress >= 100 ? '#22c55e' : progress > 50 ? '#10b981' : '#f97316'}
                        strokeWidth="6"
                        strokeDasharray={circ}
                        strokeDashoffset={strokeDashoffset}
                        strokeLinecap="round"
                        fill="none"
                        className="transition-all duration-150"
                      />
                    </svg>
                  )}

                  {/* Inner Content */}
                  <div className="flex flex-col items-center justify-center relative z-10">
                    <span className={`font-black tracking-wider drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)] ${
                      isDone
                        ? 'text-3xl text-green-300'
                        : isCurrent
                        ? 'text-3xl text-orange-200'
                        : 'text-2xl text-slate-300'
                    }`}>
                      {isDone ? '✓' : i + 1}
                    </span>

                    {isCurrent && progress > 0 && progress < 100 && (
                      <span className="text-[11px] font-mono font-black text-amber-300 bg-navy-950/90 px-1.5 py-0.2 rounded mt-0.5 border border-amber-400/50">
                        {progress}%
                      </span>
                    )}
                  </div>

                  {/* Pulsing ring when active */}
                  {isCurrent && progress < 100 && (
                    <div className="absolute inset-[-12px] rounded-full border-2 border-orange-400 animate-ping opacity-60 pointer-events-none" />
                  )}

                  {/* Subtitle / status badge underneath circle */}
                  <div className="absolute -bottom-8 pointer-events-none whitespace-nowrap z-20">
                    {isDone ? (
                      <span className="text-[11px] font-bold font-mono bg-green-950/90 text-green-300 px-2.5 py-0.5 rounded-full border border-green-500/70 shadow-lg">
                        ✓ ĐÃ LƯU ĐIỂM {i + 1}
                      </span>
                    ) : isCurrent ? (
                      <span className={`text-[11px] font-bold font-mono px-3 py-1 rounded-full border shadow-xl ${
                        progress >= 100
                          ? 'bg-green-600 text-white border-green-400 animate-bounce'
                          : progress > 0
                          ? 'bg-amber-950/95 text-amber-300 border-amber-500 animate-pulse'
                          : 'bg-navy-950/95 text-cyan-300 border-cyan-500'
                      }`}>
                        {progress >= 100
                          ? `✓ ĐÃ XONG! BƯỚC SANG ĐIỂM TIẾP THEO`
                          : progress > 0
                          ? `⏳ Đang lấy mẫu ${progress}% - Giữ yên!`
                          : `🎯 Đặt chân vào đây`}
                      </span>
                    ) : canDrag ? (
                      <span className="text-[11px] font-bold font-mono bg-navy-950/90 text-cyan-300 px-2 py-0.5 rounded-full border border-cyan-500/60 shadow-lg">
                        Điểm {i + 1} ({Math.round(t[0] * 100)}%, {Math.round(t[1] * 100)}%)
                      </span>
                    ) : (
                      <span className="text-[11px] font-mono text-slate-500">
                        Điểm {i + 1}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Floating Calibration Status & Instructions Card */}
      {isCalibrating && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30 pointer-events-none text-center max-w-xl w-full px-4">
          <div className="bg-navy-950/95 border-2 border-cyan-500/60 rounded-2xl p-4 shadow-[0_0_50px_rgba(0,0,0,0.8)] backdrop-blur-md">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-cyan-300 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping inline-block" />
                {calState?.message || `Hãy đứng chân vào Vòng tròn ${calState?.pointIndex + 1}`}
              </span>
              <span className="text-xs font-mono font-bold text-amber-400">
                {calState?.samples || 0}/{calState?.samplesNeeded || 30} ({calState?.progressPct || 0}%)
              </span>
            </div>
            
            <div className="w-full h-3 bg-navy-900 rounded-full overflow-hidden border border-cyan-500/30">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 via-amber-400 to-green-400 transition-all duration-150 rounded-full"
                style={{ width: `${calState?.progressPct || 0}%` }}
              />
            </div>

            <div className="text-[11px] text-slate-400 mt-2 flex items-center justify-between">
              <span>💡 Đứng yên ~1s để hệ thống chạy 0% ➔ 100% tự lưu</span>
              <span>Bấm <kbd className="px-1.5 py-0.5 bg-navy-800 border border-slate-600 rounded text-slate-200 font-mono text-[10px]">Space</kbd> để chốt nhanh</span>
            </div>
          </div>
        </div>
      )}

      {/* Review Modal Dialog on Wall screen */}
      {isReview && (
        <div className="absolute inset-0 flex items-center justify-center bg-navy-950/85 z-40 backdrop-blur-sm">
          <div className="bg-navy-900 border-2 border-cyan-500/70 p-8 rounded-3xl text-center max-w-lg shadow-[0_0_60px_rgba(6,182,212,0.4)]">
            <h2 className="text-3xl font-extrabold text-cyan-300 mb-2">Đo Hoàn Tất 4 Điểm!</h2>
            <div className="text-5xl font-mono font-black my-5 text-green-400">
              RMS: {calState.result?.rmsPx.toFixed(1)} px
            </div>
            <p className="text-slate-300 text-sm mb-6 leading-relaxed">
              Sai số lớn nhất: {calState.result?.maxPx.toFixed(1)} px.
              {calState.result?.ok
                ? ' Khớp rất chuẩn xác (<15px)!'
                : ' Sai số hơi cao, bạn có thể bấm đo lại nếu muốn.'}
            </p>
            <div className="flex justify-center gap-4">
              <button
                onClick={commitCal}
                className="px-6 py-3.5 bg-gradient-to-r from-green-500 to-emerald-400 hover:brightness-110 text-navy-950 font-black text-lg rounded-xl shadow-lg transition active:scale-95"
              >
                ✓ LƯU CẤU HÌNH (Commit)
              </button>
              <button
                onClick={startCal}
                className="px-6 py-3.5 bg-navy-800 hover:bg-navy-700 text-slate-200 text-lg rounded-xl border border-navy-600 transition"
              >
                ↺ Đo lại (Retry)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Debug zones rendering */}
      {showZones && config?.zones && (
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-20">
          {config.zones.map((z: any) => {
            if (!z.enabled) return null
            const isActive = zoneStates[z.id]?.count > 0
            const color = isActive ? 'var(--success)' : z.color
            const opacity = isActive ? 0.8 : 0.3
            if (z.shape.type === 'rect') {
              return (
                <rect
                  key={z.id}
                  x={`${z.shape.x * 100}%`}
                  y={`${z.shape.y * 100}%`}
                  width={`${z.shape.w * 100}%`}
                  height={`${z.shape.h * 100}%`}
                  stroke={color}
                  strokeWidth="2"
                  fill={color}
                  fillOpacity={opacity}
                />
              )
            } else if (z.shape.type === 'circle') {
              return (
                <ellipse
                  key={z.id}
                  cx={`${z.shape.cx * 100}%`}
                  cy={`${z.shape.cy * 100}%`}
                  rx={`${z.shape.r * 100}%`}
                  ry={`${z.shape.r * 100 * (config.wall.widthPx / config.wall.heightPx)}%`}
                  stroke={color}
                  strokeWidth="2"
                  fill={color}
                  fillOpacity={opacity}
                />
              )
            } else if (z.shape.type === 'polygon') {
              const pointsStr = z.shape.points.map((p: any) => `${p[0] * 100}%,${p[1] * 100}%`).join(' ')
              return (
                <polygon
                  key={z.id}
                  points={pointsStr}
                  stroke={color}
                  strokeWidth="2"
                  fill={color}
                  fillOpacity={opacity}
                />
              )
            }
            return null
          })}
        </svg>
      )}

      {/* Test mode live interactive footprint ripples */}
      {testMode && !isCalibrating && (
        <div className="absolute inset-0 z-30 pointer-events-none">
          {/* Subtle status indicator */}
          <div className="absolute top-20 left-6 bg-navy-950/80 text-cyan-300 px-3.5 py-1.5 rounded-xl border border-cyan-500/40 font-mono text-xs shadow-xl backdrop-blur-md flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse" />
            <span>ĐANG TEST TƯƠNG TÁC (Phím T để ẩn | ESC thoát)</span>
          </div>

          {(Array.isArray(blobs) ? blobs : (blobs as any)?.blobs || []).map((b: any) => {
            const u = b.u !== undefined ? b.u : (b.x !== undefined ? b.x : 0.5)
            const v = b.v !== undefined ? b.v : (b.y !== undefined ? b.y : 0.5)
            const rPx = Math.max(35, Math.min(80, b.sizeMm ? b.sizeMm / 3.5 : 45))

            return (
              <div
                key={b.id}
                className="absolute transition-all duration-75 ease-out"
                style={{
                  left: `${u * 100}%`,
                  top: `${v * 100}%`,
                  transform: 'translate(-50%, -50%)',
                }}
              >
                {/* Expanding pulse ripple */}
                <div
                  className="absolute inset-0 rounded-full border-2 border-cyan-400 animate-ping opacity-60"
                  style={{ width: rPx * 2, height: rPx * 2, margin: -rPx }}
                />

                {/* Glowing neon halo ring */}
                <div
                  className="rounded-full bg-gradient-to-tr from-cyan-500/35 via-teal-400/25 to-blue-500/15 border-2 border-cyan-300 shadow-[0_0_40px_rgba(6,182,212,0.9)] flex items-center justify-center backdrop-blur-xs"
                  style={{ width: rPx * 2, height: rPx * 2 }}
                >
                  {/* Inner bright core */}
                  <div className="w-4 h-4 rounded-full bg-white shadow-[0_0_20px_#fff]" />
                </div>

                {/* Floating info badge */}
                <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 bg-navy-950/95 text-cyan-200 text-xs font-bold px-3 py-1 rounded-full border border-cyan-500/60 whitespace-nowrap shadow-xl flex items-center gap-1.5 font-mono">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  ID #{b.id} ({Math.round(u * 100)}%, {Math.round(v * 100)}%)
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Footer shortcut hints */}
      <div className="absolute bottom-2 right-6 z-20 text-slate-500 text-xs pointer-events-none">
        F: Fullscreen | ESC: Thoát | T: Test | D: Zones | H: Menu
      </div>
    </div>
  )
}
