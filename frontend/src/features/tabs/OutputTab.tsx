import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, fetchConfig } from '../../api/rest'
import { useI18n } from '../../i18n'

export default function OutputTab() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })

  const updateConfig = useMutation({
    mutationFn: (newCfg: any) => api.put('/api/config', newCfg),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  if (!config) return null
  const osc = config.output.osc
  const tuio = config.output.tuio

  return (
    <div className="space-y-4">
      {/* OSC Config */}
      <div className="panel-section">
        <div className="flex justify-between items-center mb-4">
          <label className="label-neon flex items-center space-x-2 m-0 cursor-pointer">
            <input type="checkbox" checked={osc.enabled} onChange={e => updateConfig.mutate({...config, output: {...config.output, osc: {...osc, enabled: e.target.checked}}})} className="w-4 h-4 accent-neon-cyan" />
            <span>{t.output.osc}</span>
          </label>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label-neon">{t.output.host}</label>
            <input type="text" value={osc.host} onChange={e => updateConfig.mutate({...config, output: {...config.output, osc: {...osc, host: e.target.value}}})} className="input-neon w-full" />
          </div>
          <div>
            <label className="label-neon">{t.output.port}</label>
            <input type="number" value={osc.port} onChange={e => updateConfig.mutate({...config, output: {...config.output, osc: {...osc, port: +e.target.value}}})} className="input-neon w-full" />
          </div>
        </div>
      </div>

      {/* TUIO Config */}
      <div className="panel-section">
        <div className="flex justify-between items-center mb-4">
          <label className="label-neon flex items-center space-x-2 m-0 cursor-pointer">
            <input type="checkbox" checked={tuio.enabled} onChange={e => updateConfig.mutate({...config, output: {...config.output, tuio: {...tuio, enabled: e.target.checked}}})} className="w-4 h-4 accent-neon-cyan" />
            <span>{t.output.tuio}</span>
          </label>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label-neon">{t.output.host}</label>
            <input type="text" value={tuio.host} onChange={e => updateConfig.mutate({...config, output: {...config.output, tuio: {...tuio, host: e.target.value}}})} className="input-neon w-full" />
          </div>
          <div>
            <label className="label-neon">{t.output.port}</label>
            <input type="number" value={tuio.port} onChange={e => updateConfig.mutate({...config, output: {...config.output, tuio: {...tuio, port: +e.target.value}}})} className="input-neon w-full" />
          </div>
        </div>
      </div>

      <button className="btn-neon w-full">{t.output.testSend}</button>
    </div>
  )
}
