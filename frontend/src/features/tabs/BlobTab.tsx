import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, fetchConfig } from '../../api/rest'
import { useI18n } from '../../i18n'
import { useEffect, useState } from 'react'

export default function InputTab() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })

  const updateConfig = useMutation({
    mutationFn: (newCfg: any) => api.put('/api/config', newCfg),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  // Debounced update for sliders
  const [localCfg, setLocalCfg] = useState<any>(config?.blob)
  useEffect(() => { setLocalCfg(config?.blob) }, [config?.blob])

  const handleApply = (key: string, val: number) => {
    setLocalCfg((p: any) => ({ ...p, [key]: val }))
    if (!config) return
    const newCfg = { ...config, blob: { ...config.blob, [key]: val } }
    updateConfig.mutate(newCfg) // Or debounce this call if needed
  }

  if (!config) return null

  return (
    <div className="space-y-4">
      <div className="panel-section">
        <label className="label-neon">{t.blob.clusterGap}</label>
        <div className="flex items-center space-x-4">
          <input 
            type="range" min="10" max="200" step="5"
            value={localCfg?.clusterGapMm || 0}
            onChange={e => setLocalCfg({ ...localCfg, clusterGapMm: +e.target.value })}
            onMouseUp={e => handleApply('clusterGapMm', +(e.target as HTMLInputElement).value)}
            className="flex-1 accent-neon-cyan" 
          />
          <span className="w-12 text-right">{localCfg?.clusterGapMm}</span>
        </div>
      </div>

      <div className="panel-section">
        <label className="label-neon">{t.blob.minPoints}</label>
        <div className="flex items-center space-x-4">
          <input 
            type="range" min="1" max="50" step="1"
            value={localCfg?.minPoints || 0}
            onChange={e => setLocalCfg({ ...localCfg, minPoints: +e.target.value })}
            onMouseUp={e => handleApply('minPoints', +(e.target as HTMLInputElement).value)}
            className="flex-1 accent-neon-magenta" 
          />
          <span className="w-12 text-right">{localCfg?.minPoints}</span>
        </div>
      </div>

      <div className="panel-section grid grid-cols-2 gap-4">
        <div>
          <label className="label-neon">{t.blob.minSize}</label>
          <input 
            type="number" 
            value={localCfg?.minSizeMm || 0}
            onChange={e => handleApply('minSizeMm', +e.target.value)}
            className="input-neon w-full"
          />
        </div>
        <div>
          <label className="label-neon">{t.blob.maxSize}</label>
          <input 
            type="number" 
            value={localCfg?.maxSizeMm || 0}
            onChange={e => handleApply('maxSizeMm', +e.target.value)}
            className="input-neon w-full"
          />
        </div>
      </div>

      <div className="panel-section">
        <label className="label-neon">{t.blob.smoothing}</label>
        <div className="flex items-center space-x-4">
          <input 
            type="range" min="0" max="1" step="0.05"
            value={localCfg?.smoothing || 0}
            onChange={e => setLocalCfg({ ...localCfg, smoothing: +e.target.value })}
            onMouseUp={e => handleApply('smoothing', +(e.target as HTMLInputElement).value)}
            className="flex-1 accent-neon-cyan" 
          />
          <span className="w-12 text-right">{localCfg?.smoothing?.toFixed(2)}</span>
        </div>
      </div>

      <div className="panel-section">
        <label className="label-neon">{t.blob.lostFrames}</label>
        <div className="flex items-center space-x-4">
          <input 
            type="range" min="0" max="10" step="1"
            value={localCfg?.lostFrames || 0}
            onChange={e => setLocalCfg({ ...localCfg, lostFrames: +e.target.value })}
            onMouseUp={e => handleApply('lostFrames', +(e.target as HTMLInputElement).value)}
            className="flex-1 accent-neon-yellow" 
          />
          <span className="w-12 text-right">{localCfg?.lostFrames}</span>
        </div>
      </div>
    </div>
  )
}
