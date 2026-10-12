import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, fetchConfig, fetchLidars, connectLidar, disconnectLidar } from '../../api/rest'
import { useWsStore } from '../../api/ws'
import { useI18n } from '../../i18n'
import { useState } from 'react'

export default function LidarList() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const { data: lidarsStatus, refetch } = useQuery({ queryKey: ['lidarsStatus'], queryFn: fetchLidars })
  
  const statuses = useWsStore(s => s.lidarStatuses)
  const calState = useWsStore(s => s.calibrationState)
  
  const updateConfig = useMutation({
    mutationFn: (newCfg: any) => api.put('/api/config', newCfg),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  const toggle = async (id: string, st: string) => {
    if (st === 'connected') {
      await disconnectLidar(id)
    } else {
      await connectLidar(id)
      const idx = lidars.findIndex((l: any) => l.id === id)
      if (idx !== -1 && !lidars[idx].enabled) {
        updateLidarConfig(idx, { enabled: true })
      }
    }
    refetch()
  }

  const startCal = (id: string) => api.post('/api/calibration/start', { lidarId: id }).catch(console.error)
  const cancelCal = () => api.post('/api/calibration/cancel', {}).catch(console.error)
  const commitCal = () => api.post('/api/calibration/commit', {}).catch(console.error)

  const [showAddForm, setShowAddForm] = useState(false)
  const [newType, setNewType] = useState('serial')

  if (!config) return null
  const lidars = config.lidars || []

  const updateLidarConfig = (idx: number, updates: any) => {
    const newLidars = [...lidars]
    newLidars[idx] = { ...newLidars[idx], ...updates }
    updateConfig.mutate({ ...config, lidars: newLidars })
  }

  const deleteLidar = (idx: number) => {
    const newLidars = [...lidars]
    newLidars.splice(idx, 1)
    updateConfig.mutate({ ...config, lidars: newLidars })
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-2">
        <h2 className="font-bold uppercase tracking-widest">{t.lidar.title}</h2>
        <button onClick={() => setShowAddForm(!showAddForm)} className="btn-neon !py-1 text-xs">{t.lidar.add}</button>
      </div>

      {showAddForm && (
        <div className="panel-section bg-navy-800">
          <div className="flex space-x-2 mb-2">
            <select value={newType} onChange={e => setNewType(e.target.value)} className="input-neon flex-1">
              <option value="serial">Serial (USB)</option>
              <option value="tcp">TCP (Network)</option>
              <option value="simulator">Simulator</option>
            </select>
            <button className="btn-neon flex-1 text-xs">{t.lidar.probe}</button>
          </div>
          <button onClick={() => setShowAddForm(false)} className="btn-neon-danger w-full text-xs">Cancel</button>
        </div>
      )}

      {lidars.map((l: any, idx: number) => {
        const id = l.id
        const stObj = lidarsStatus?.find((x: any) => x.config.id === id)?.status || { state: 'disconnected', fps: 0 }
        const st = statuses[id]?.state || stObj.state
        const fps = statuses[id]?.fps || stObj.fps
        
        const isCalibrating = calState?.lidarId === id && !['IDLE', 'COMMITTED', 'CANCELLED', 'FAILED'].includes(calState.state)
        const isReview = calState?.state === 'REVIEW' && calState?.lidarId === id
        
        return (
          <div key={id} className={`panel-section ${isCalibrating ? 'border-neon-cyan ring-1 ring-neon-cyan/50' : ''}`}>
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center space-x-2">
                <input 
                  type="checkbox" 
                  checked={l.enabled} 
                  onChange={e => updateLidarConfig(idx, { enabled: e.target.checked })} 
                  className="w-4 h-4 accent-neon-cyan"
                  title="Tự động kết nối khi mở app (Auto-start)"
                />
                <input 
                  type="text" 
                  value={l.name} 
                  onChange={e => updateLidarConfig(idx, { name: e.target.value })}
                  className="bg-navy-950 text-token text-sm font-bold px-2 py-1 rounded w-32 border border-navy-700 focus:border-neon-cyan"
                />
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full shadow-[0_0_8px] ${st === 'connected' ? 'bg-green-500 shadow-green-500' : st === 'error' ? 'bg-red-500 shadow-red-500' : 'bg-yellow-500 shadow-yellow-500'}`} />
                <button onClick={() => deleteLidar(idx)} className="text-red-500 hover:text-red-400">🗑</button>
              </div>
            </div>
            
            <div className="flex flex-col gap-2 mb-3">
              <div className="text-xs text-slate-400 font-mono flex justify-between">
                <span>{(l.connection?.kind ?? l.model ?? 'LIDAR').toUpperCase()} | {l.model}</span>
                <span className="text-neon-cyan">{fps.toFixed(1)} FPS</span>
              </div>
              {l.connection?.kind === 'serial' && (
                <div className="flex space-x-2 text-xs">
                  <div className="flex-1">
                    <span className="block mb-1 text-slate-400">Port (COM)</span>
                    <input type="text" value={l.connection.port} onChange={e => updateLidarConfig(idx, { connection: { ...l.connection, port: e.target.value }})} className="input-neon w-full !py-1" disabled={st === 'connected'} />
                  </div>
                  <div className="flex-1">
                    <span className="block mb-1 text-slate-400">Baudrate</span>
                    <input type="number" value={l.connection.baud} onChange={e => updateLidarConfig(idx, { connection: { ...l.connection, baud: +e.target.value }})} className="input-neon w-full !py-1" disabled={st === 'connected'} />
                  </div>
                </div>
              )}
              {l.connection?.kind === 'tcp' && (
                <div className="flex space-x-2 text-xs">
                  <div className="flex-[2]">
                    <span className="block mb-1 text-slate-400">IP (Host)</span>
                    <input type="text" value={l.connection.host} onChange={e => updateLidarConfig(idx, { connection: { ...l.connection, host: e.target.value }})} className="input-neon w-full !py-1" disabled={st === 'connected'} />
                  </div>
                  <div className="flex-1">
                    <span className="block mb-1 text-slate-400">Port</span>
                    <input type="number" value={l.connection.port} onChange={e => updateLidarConfig(idx, { connection: { ...l.connection, port: +e.target.value }})} className="input-neon w-full !py-1" disabled={st === 'connected'} />
                  </div>
                </div>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-2 mb-3">
              <label className="flex items-center space-x-2 text-xs">
                <input type="checkbox" checked={l.transform.flipX} onChange={e => updateLidarConfig(idx, { transform: { ...l.transform, flipX: e.target.checked }})} className="accent-neon-cyan" />
                <span>{t.lidar.flipX}</span>
              </label>
              <label className="flex items-center space-x-2 text-xs">
                <input type="checkbox" checked={l.transform.flipY} onChange={e => updateLidarConfig(idx, { transform: { ...l.transform, flipY: e.target.checked }})} className="accent-neon-cyan" />
                <span>{t.lidar.flipY}</span>
              </label>
              <div className="col-span-2 flex space-x-2 text-xs">
                <div className="flex-1">
                  <span className="block mb-1 text-slate-400">{t.lidar.rotation}</span>
                  <input type="number" value={l.transform.rotationDeg} onChange={e => updateLidarConfig(idx, { transform: { ...l.transform, rotationDeg: +e.target.value }})} className="input-neon w-full !py-1" />
                </div>
                <div className="flex-1">
                  <span className="block mb-1 text-slate-400">Off X/Y</span>
                  <div className="flex space-x-1">
                    <input type="number" value={l.transform.offsetMm[0]} onChange={e => updateLidarConfig(idx, { transform: { ...l.transform, offsetMm: [+e.target.value, l.transform.offsetMm[1]] }})} className="input-neon w-full !py-1" />
                    <input type="number" value={l.transform.offsetMm[1]} onChange={e => updateLidarConfig(idx, { transform: { ...l.transform, offsetMm: [l.transform.offsetMm[0], +e.target.value] }})} className="input-neon w-full !py-1" />
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex space-x-2">
              <button 
                onClick={() => toggle(id, st)}
                className={`flex-1 ${st === 'connected' ? 'btn-neon-danger' : 'btn-neon'} !text-xs`}
              >
                {st === 'connected' ? 'Disconnect' : 'Connect'}
              </button>
              
              {!isCalibrating && (
                <button 
                  onClick={() => startCal(id)}
                  disabled={st !== 'connected'}
                  className="flex-1 btn-neon !text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Calibrate
                </button>
              )}
            </div>

            {isCalibrating && (
              <div className="mt-3 p-3 bg-navy-950/50 rounded border border-neon-cyan/30">
                <div className="text-neon-cyan font-bold mb-1 text-sm">Cal: {calState.state}</div>
                <div className="text-xs text-slate-300 mb-3">{calState.message}</div>
                
                {isReview ? (
                  <div className="flex flex-col space-y-2">
                    <div className="text-xs bg-navy-900 p-2 rounded text-slate-300 font-mono">
                      RMS: <span className={calState.result?.ok ? 'text-green-400' : 'text-red-400'}>{calState.result?.rmsPx.toFixed(1)}</span> px <br/>
                      Max: {calState.result?.maxPx.toFixed(1)} px
                    </div>
                    <div className="flex space-x-2">
                      <button onClick={commitCal} className="flex-1 py-1 bg-green-600/80 hover:bg-green-500 rounded text-xs font-bold text-on-accent">Commit</button>
                      <button onClick={() => startCal(id)} className="flex-1 py-1 bg-neon-orange/80 hover:bg-neon-orange rounded text-xs font-bold text-on-accent">Retry</button>
                    </div>
                  </div>
                ) : (
                  <div className="flex space-x-2">
                    <button onClick={cancelCal} className="flex-1 btn-neon-danger !py-1 !text-xs">Cancel</button>
                    <button onClick={() => api.post('/api/calibration/capture', {}).catch(console.error)} className="flex-1 btn-neon !py-1 !text-xs">Capture</button>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
