import { useQuery } from '@tanstack/react-query'
import { fetchConfig } from '../../api/rest'
import { useWsStore } from '../../api/ws'

export default function CoverageList({ onSelect, activeLidarId }: { onSelect: (id: string | null) => void, activeLidarId: string | null }) {
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const statuses = useWsStore(s => s.lidarStatuses)

  if (!config) return null

  return (
    <div className="space-y-2">
      <h2 className="font-bold uppercase tracking-widest text-slate-400 mb-4">Lidar Coverage</h2>
      {config.lidars.map((l: any) => {
        const isOffline = statuses[l.id]?.state !== 'connected'
        const isActive = activeLidarId === l.id
        return (
          <div 
            key={l.id} 
            className={`panel-section cursor-pointer transition-colors flex justify-between items-center ${isActive ? 'border-neon-cyan bg-neon-cyan/5' : 'hover:border-slate-500'}`}
            onClick={() => onSelect(l.id)}
          >
            <span className={`font-bold ${isActive ? 'text-neon-cyan' : ''}`}>{l.name}</span>
            {isOffline ? (
              <span className="bg-red-900/50 text-red-400 text-xs px-2 py-1 rounded border border-red-500/50">OFFLINE</span>
            ) : (
              <span className="bg-green-900/50 text-green-400 text-xs px-2 py-1 rounded border border-green-500/50">ONLINE</span>
            )}
          </div>
        )
      })}
    </div>
  )
}
