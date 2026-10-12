import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, fetchConfig } from '../../api/rest'
import { useI18n } from '../../i18n'

interface DisplayInfo {
  index: number
  x: number
  y: number
  width: number
  height: number
  primary: boolean
}

declare global {
  interface Window {
    pywebview?: {
      api?: {
        list_screens: () => Promise<DisplayInfo[]>
        open_wall: (screenIndex: number) => Promise<boolean>
        close_wall: () => Promise<boolean>
      }
    }
  }
}

export default function SettingsTab() {
  const { t, lang, setLang } = useI18n()
  const queryClient = useQueryClient()
  const [screens, setScreens] = useState<DisplayInfo[]>([])
  const [screenIndex, setScreenIndex] = useState(0)
  const [wallPopup, setWallPopup] = useState<Window | null>(null)
  const { data: config } = useQuery({ queryKey: ['config'], queryFn: fetchConfig })

  useEffect(() => {
    const loadScreens = () => {
      void window.pywebview?.api?.list_screens().then(setScreens).catch(console.error)
    }
    loadScreens()
    window.addEventListener('pywebviewready', loadScreens)
    return () => window.removeEventListener('pywebviewready', loadScreens)
  }, [])

  const updateConfig = useMutation({
    mutationFn: (newCfg: any) => api.put('/api/config', newCfg),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] })
  })

  if (!config) return null

  const handleExport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(config, null, 2))
    const downloadAnchorNode = document.createElement('a')
    downloadAnchorNode.setAttribute("href", dataStr)
    downloadAnchorNode.setAttribute("download", "config.json")
    document.body.appendChild(downloadAnchorNode)
    downloadAnchorNode.click()
    downloadAnchorNode.remove()
  }

  const setTheme = (key: 'theme' | 'wallTheme', value: 'light' | 'dark') => {
    const updated = { ...config, ui: { ...config.ui, [key]: value } }
    if (key === 'theme') document.documentElement.dataset.theme = value
    updateConfig.mutate(updated)
  }

  const openWall = async () => {
    if (window.pywebview?.api) {
      await window.pywebview.api.open_wall(screenIndex)
      return
    }
    setWallPopup(window.open('/wall', 'lidar-wall', 'popup,width=1440,height=900'))
  }

  return (
    <div className="space-y-4">
      <div className="panel-section grid grid-cols-2 gap-4">
        <div>
          <label className="label-neon">{t.settings.wallWidth}</label>
          <input 
            type="number" 
            value={config.wall.widthPx} 
            onChange={e => updateConfig.mutate({...config, wall: {...config.wall, widthPx: +e.target.value}})} 
            className="input-neon w-full" 
          />
        </div>
        <div>
          <label className="label-neon">{t.settings.wallHeight}</label>
          <input 
            type="number" 
            value={config.wall.heightPx} 
            onChange={e => updateConfig.mutate({...config, wall: {...config.wall, heightPx: +e.target.value}})} 
            className="input-neon w-full" 
          />
        </div>
      </div>

      <div className="panel-section">
        <label className="label-neon">{t.settings.lang}</label>
        <div className="flex space-x-2">
          <button onClick={() => setLang('vi')} className={`flex-1 py-1 rounded border ${lang === 'vi' ? 'bg-cyan-900 border-cyan-500' : 'bg-navy-800 border-navy-600'}`}>Tiếng Việt</button>
          <button onClick={() => setLang('en')} className={`flex-1 py-1 rounded border ${lang === 'en' ? 'bg-cyan-900 border-cyan-500' : 'bg-navy-800 border-navy-600'}`}>English</button>
        </div>
      </div>

      <div className="panel-section space-y-3">
        <div>
          <span className="label-neon">Giao diện điều khiển</span>
          <div className="flex" role="group" aria-label="Giao diện điều khiển">
            {(['light', 'dark'] as const).map(theme => (
              <button key={theme} aria-pressed={(config.ui?.theme ?? 'light') === theme} onClick={() => setTheme('theme', theme)} className={`flex-1 border px-3 py-2 text-sm font-bold first:rounded-l last:rounded-r ${(config.ui?.theme ?? 'light') === theme ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' : 'border-navy-700 text-slate-500'}`}>
                {theme === 'light' ? 'Sáng' : 'Tối'}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="label-neon">Giao diện Wall</span>
          <div className="flex" role="group" aria-label="Giao diện Wall">
            {(['dark', 'light'] as const).map(theme => (
              <button key={theme} aria-pressed={(config.ui?.wallTheme ?? 'dark') === theme} onClick={() => setTheme('wallTheme', theme)} className={`flex-1 border px-3 py-2 text-sm font-bold first:rounded-l last:rounded-r ${(config.ui?.wallTheme ?? 'dark') === theme ? 'border-neon-cyan bg-neon-cyan/10 text-neon-cyan' : 'border-navy-700 text-slate-500'}`}>
                {theme === 'light' ? 'Sáng' : 'Tối'}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="panel-section space-y-3">
        <span className="label-neon">Cửa sổ Wall</span>
        {screens.length > 0 && (
          <select value={screenIndex} onChange={event => setScreenIndex(Number(event.target.value))} className="input-neon w-full">
            {screens.map(screen => (
              <option key={screen.index} value={screen.index}>
                Màn hình {screen.index + 1}{screen.primary ? ' (chính)' : ''} · {screen.width} × {screen.height}
              </option>
            ))}
          </select>
        )}
        <div className="flex gap-2">
          <button onClick={() => void openWall()} className="btn-neon flex-1">Mở Wall toàn màn hình</button>
          {window.pywebview?.api ? (
            <button onClick={() => void window.pywebview?.api?.close_wall()} className="btn-neon-danger">Đóng Wall</button>
          ) : (
            <button onClick={() => { wallPopup?.close(); setWallPopup(null) }} className="btn-neon-danger">Đóng Wall</button>
          )}
        </div>
      </div>

      <div className="flex space-x-2">
        <button onClick={handleExport} className="btn-neon flex-1">{t.settings.exportConfig}</button>
        {/* Import could be a file input, omitting for brevity */}
      </div>
    </div>
  )
}
