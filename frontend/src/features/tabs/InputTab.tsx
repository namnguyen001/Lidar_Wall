import { useQuery } from '@tanstack/react-query'
import { fetchConfig } from '../../api/rest'
import { api } from '../../api/rest'
import { useI18n } from '../../i18n'
import { useState, useEffect } from 'react'

export default function InputTab() {
  const { t } = useI18n()
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  const [bgStatus, setBgStatus] = useState<any>({})

  useEffect(() => {
    const onBgLearn = (e: any) => setBgStatus(e.detail)
    window.addEventListener('bgLearn', onBgLearn)
    return () => window.removeEventListener('bgLearn', onBgLearn)
  }, [])

  if (!config) return null
  const lidars = config.lidars || []

  const relearnBg = async (id: string) => {
    // Requires a backend endpoint, e.g., /api/lidars/{id}/learn-bg
    await api.post(`/api/lidars/${id}/learn-bg`, {}).catch(console.error)
  }

  return (
    <div className="space-y-4">
      <div className="panel-section">
        <label className="label-neon">{t.input.bgLearning}</label>
        {lidars.map((l: any) => (
          <div key={l.id} className="flex justify-between items-center bg-navy-800 p-2 rounded mb-2">
            <span className="font-bold">{l.id}</span>
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400">
                {bgStatus.id === l.id && bgStatus.status === 'learning' ? `${Math.round(bgStatus.progress * 100)}%` : 'Ready'}
              </span>
              <button onClick={() => relearnBg(l.id)} className="btn-neon text-xs py-1 px-2">{t.input.reLearn}</button>
            </div>
          </div>
        ))}
      </div>
      
      {/* Could also add global tolerance or min/max range here if defined in config schema */}
    </div>
  )
}
