import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchConfig } from '../api/rest'
import LidarList from '../features/lidar/LidarList'
import TopViewCanvas from '../features/topview/TopViewCanvas'
import ZoneList from '../features/zones/ZoneList'
import WallPreview from '../features/zones/WallPreview'
import InputTab from '../features/tabs/InputTab'
import BlobTab from '../features/tabs/BlobTab'
import OutputTab from '../features/tabs/OutputTab'
import SettingsTab from '../features/tabs/SettingsTab'
import CoverageList from '../features/coverage/CoverageList'
import { useI18n } from '../i18n'
import { useWsStore } from '../api/ws'

export default function ControlPage() {
  const configQuery = useQuery({ queryKey: ['config'], queryFn: fetchConfig })
  useEffect(() => {
    document.documentElement.dataset.theme = configQuery.data?.ui?.theme === 'dark' ? 'dark' : 'light'
  }, [configQuery.data])
  const { t } = useI18n()
  const { eventsConnected } = useWsStore()
  const [activeTab, setActiveTab] = useState('Lidar')
  const [activeZone, setActiveZone] = useState<any>(null)
  const [activeLidarId, setActiveLidarId] = useState<string | null>(null)
  
  const tabs = [
    { id: 'Lidar', label: t.tabs.lidar },
    { id: 'Input', label: t.tabs.input },
    { id: 'Blob', label: t.tabs.blob },
    { id: 'Coverage', label: 'Coverage' },
    { id: 'Zones', label: t.tabs.zones },
    { id: 'Output', label: t.tabs.output },
    { id: 'Settings', label: t.tabs.settings }
  ]

  if (configQuery.isPending) {
    return <main data-testid="control-page" className="flex h-screen items-center justify-center bg-navy-950 text-slate-200">Đang tải…</main>
  }
  if (configQuery.isError) {
    return (
      <main data-testid="control-page" className="flex h-screen flex-col items-center justify-center gap-4 bg-navy-950 p-6 text-slate-200">
        <h1 className="text-xl font-bold">Không tải được cấu hình</h1>
        <p role="alert" className="text-red-300">{configQuery.error.message}</p>
        <button onClick={() => void configQuery.refetch()} className="btn-neon">Thử lại</button>
      </main>
    )
  }

  return (
    <div data-testid="control-page" className="flex flex-col md:flex-row h-screen bg-navy-950 text-slate-200 overflow-hidden font-sans">
      {!eventsConnected && (
        <div className="absolute top-0 left-0 right-0 bg-red-600 text-on-accent font-bold text-center py-1 z-50 animate-pulse shadow-lg">
          {t.common.disconnected}
        </div>
      )}
      
      <div className="flex-1 relative bg-navy-900 m-2 rounded-xl overflow-hidden shadow-2xl border border-navy-700 min-h-[300px] md:min-h-0 lidar-display-area">
        {activeTab === 'Zones' ? (
          <WallPreview activeZone={activeZone} mode="zone" />
        ) : activeTab === 'Coverage' ? (
          <WallPreview activeLidarId={activeLidarId} mode="coverage" />
        ) : (
          <TopViewCanvas />
        )}
      </div>
      
      <div className="w-full h-1/2 md:w-[400px] md:h-full border-t md:border-t-0 md:border-l border-navy-700 bg-navy-950 flex flex-col z-10 shadow-[0_-10px_30px_rgba(0,0,0,0.5)] md:shadow-[-10px_0_30px_rgba(0,0,0,0.5)]">
        <div className="flex flex-wrap border-b border-navy-800 bg-navy-900/50">
          {tabs.map(tab => (
            <button 
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 min-w-[30%] py-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${activeTab === tab.id ? 'border-neon-cyan text-neon-cyan bg-neon-cyan/5' : 'border-transparent text-slate-500 hover:bg-navy-800 hover:text-slate-300'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
          {activeTab === 'Lidar' && <LidarList />}
          {activeTab === 'Input' && <InputTab />}
          {activeTab === 'Blob' && <BlobTab />}
          {activeTab === 'Coverage' && <CoverageList onSelect={setActiveLidarId} activeLidarId={activeLidarId} />}
          {activeTab === 'Zones' && <ZoneList onSelectZone={setActiveZone} />}
          {activeTab === 'Output' && <OutputTab />}
          {activeTab === 'Settings' && <SettingsTab />}
        </div>
      </div>
    </div>
  )
}
