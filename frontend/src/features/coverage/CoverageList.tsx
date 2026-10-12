import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchConfig, api } from '../../api/rest'
import { useWsStore } from '../../api/ws'

export default function CoverageList({ onSelect, activeLidarId }: { onSelect: (id: string | null) => void, activeLidarId: string | null }) {
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const queryClient = useQueryClient()
  const statuses = useWsStore(s => s.lidarStatuses)

  const updateConfig = useMutation({
    mutationFn: (newCfg: any) => api.put('/api/config', newCfg),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  if (!config) return null

  const resetFullCoverage = (lidarId: string) => {
    const idx = config.lidars.findIndex((l: any) => l.id === lidarId)
    if (idx < 0) return
    const newLidars = [...config.lidars]
    newLidars[idx] = {
      ...newLidars[idx],
      coverageUv: [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    }
    updateConfig.mutate({ ...config, lidars: newLidars })
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-bold uppercase tracking-widest text-slate-400 mb-1">Lidar Coverage</h2>
        <p className="text-xs text-slate-400 leading-relaxed mb-3">
          Phạm vi hiển thị của LiDAR trên màn hình chiếu. Nếu bạn dùng <strong>1 LiDAR</strong>, hãy để phủ toàn màn hình (100%).
        </p>
      </div>

      <div className="space-y-2">
        {config.lidars.map((l: any) => {
          const isOffline = statuses[l.id]?.state !== 'connected'
          const isActive = activeLidarId === l.id
          return (
            <div 
              key={l.id} 
              className={`panel-section cursor-pointer transition-colors flex flex-col gap-2 ${isActive ? 'border-neon-cyan bg-neon-cyan/5' : 'hover:border-slate-500'}`}
              onClick={() => onSelect(l.id)}
            >
              <div className="flex justify-between items-center">
                <span className={`font-bold ${isActive ? 'text-neon-cyan' : ''}`}>{l.name}</span>
                {isOffline ? (
                  <span className="bg-red-900/50 text-red-400 text-xs px-2 py-0.5 rounded border border-red-500/50">OFFLINE</span>
                ) : (
                  <span className="bg-green-900/50 text-green-400 text-xs px-2 py-0.5 rounded border border-green-500/50">ONLINE</span>
                )}
              </div>

              {isActive && (
                <div className="pt-2 border-t border-slate-700/50 flex justify-between items-center">
                  <span className="text-[11px] text-slate-400 font-mono">
                    {l.coverageUv ? 'Đang tùy biến góc' : 'Toàn màn hình'}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      resetFullCoverage(l.id)
                    }}
                    className="text-xs px-2.5 py-1 bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-500/50 rounded transition"
                    title="Đặt lại vùng phủ 100% toàn màn hình"
                  >
                    ↺ Toàn màn hình (100%)
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="p-3 bg-navy-950/80 border border-slate-700/60 rounded-xl text-xs text-slate-300 space-y-1.5">
        <div className="font-bold text-cyan-400 flex items-center gap-1.5">
          <span>💡</span> Hướng dẫn Coverage & Ghép màn hình:
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          • <strong>1 LiDAR:</strong> Bấm <em>"Toàn màn hình (100%)"</em> để phủ trọn vẹn màn chiếu.<br/>
          • <strong>2 LiDAR ghép cạnh nhau:</strong> Kéo LiDAR 1 phủ nửa bên trái (0.0 ➔ 0.55), LiDAR 2 phủ nửa bên phải (0.45 ➔ 1.0).
        </p>
      </div>
    </div>
  )
}
