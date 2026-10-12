import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, fetchConfig } from '../../api/rest'

export default function ZoneList({ onSelectZone }: { onSelectZone: (z: any) => void }) {
  const queryClient = useQueryClient()
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  
  const zones = config?.zones || []
  
  // Sort by layer desc
  const sortedZones = [...zones].sort((a, b) => b.layer - a.layer)

  const updateZoneMut = useMutation({
    mutationFn: (z: any) => api.put('/api/config', { ...config, zones: config.zones.map((x: any) => x.id === z.id ? z : x) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  const duplicateMut = useMutation({
    mutationFn: (id: string) => api.post(`/api/zones/${id}/duplicate`, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => fetch(`/api/zones/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })
  
  const addZone = async () => {
    const id = `zone_${Math.random().toString(36).substring(2, 9)}`
    const newZone = {
      id,
      name: "New Zone",
      enabled: true,
      layer: 0,
      color: getComputedStyle(document.documentElement).getPropertyValue('--accent-cyan').trim(),
      shape: { type: "rect", x: 0.4, y: 0.4, w: 0.2, h: 0.2 },
      trigger: "enter",
      dwellMs: 0,
      repeatMs: 0,
      minBlobs: 1,
      cooldownMs: 0,
      hysteresisUv: 0.005,
      exclusiveGroup: null,
      output: {}
    }
    await api.post('/api/zones', newZone)
    queryClient.invalidateQueries({ queryKey: ['config'] })
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-bold">Zones ({zones.length})</h2>
        <button onClick={addZone} className="px-3 py-1 bg-cyan-700 hover:bg-cyan-600 rounded text-sm font-bold">+ Add</button>
      </div>
      
      {sortedZones.map((z: any) => (
        <div key={z.id} className={`p-3 bg-slate-700 rounded shadow border-l-4`} style={{ borderLeftColor: z.color }}>
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-2">
              <input 
                type="checkbox" 
                checked={z.enabled} 
                onChange={e => updateZoneMut.mutate({ ...z, enabled: e.target.checked })} 
                className="w-4 h-4 accent-cyan-500"
              />
              <input 
                type="text" 
                value={z.name} 
                onChange={e => updateZoneMut.mutate({ ...z, name: e.target.value })}
                className="bg-navy-800 text-token text-sm font-bold px-2 py-1 rounded w-32 border border-navy-700 focus:border-cyan-500"
              />
            </div>
            
            <div className="flex space-x-2">
              <button onClick={() => onSelectZone(z)} className="p-1 hover:bg-slate-600 rounded" title="Edit on Wall">✏️</button>
              <button onClick={() => duplicateMut.mutate(z.id)} className="p-1 hover:bg-slate-600 rounded" title="Duplicate">📋</button>
              <button onClick={() => deleteMut.mutate(z.id)} className="p-1 hover:bg-slate-600 rounded text-red-400" title="Delete">🗑️</button>
            </div>
          </div>
          
          <div className="mt-2 flex items-center space-x-3 text-xs text-slate-300">
            <div>Shape: {z.shape.type}</div>
            <div>Trigger: {z.trigger}</div>
            <div className="flex items-center space-x-1">
              <span>Color:</span>
              <input 
                type="color" 
                value={z.color}
                onChange={e => updateZoneMut.mutate({ ...z, color: e.target.value })}
                className="w-4 h-4 border-none p-0 cursor-pointer"
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
