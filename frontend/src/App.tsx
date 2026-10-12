import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import { Component, type ErrorInfo, type ReactNode } from 'react'
import ControlPage from './routes/ControlPage'
import WallPage from './routes/WallPage'
import { useWsStore } from './api/ws'
import { useEffect, useState } from 'react'

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean, error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center w-screen h-screen bg-navy-950 text-token p-4">
          <h1 className="text-3xl text-red-500 font-bold mb-4">Ứng dụng gặp lỗi</h1>
          <p className="text-red-300 font-mono text-sm bg-navy-900 p-4 rounded mb-2 max-w-full">{this.state.error?.message}</p>
          <pre className="text-slate-400 font-mono text-xs bg-navy-900 p-4 rounded mb-4 overflow-auto max-w-full max-h-[50vh]">
            {this.state.error?.stack?.split('\n').slice(0, 8).join('\n') ?? 'Không có stack trace.'}
          </pre>
          <button 
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-neon-cyan text-navy-950 font-bold rounded"
          >
            Tải lại
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center w-screen h-screen bg-navy-950 text-token">
      <h1 className="text-4xl font-bold mb-4">Không tìm thấy trang</h1>
      <Link to="/control" className="text-neon-cyan hover:underline text-xl">
        Về trang điều khiển
      </Link>
    </div>
  )
}

function GlobalErrorBanner() {
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    const onError = (event: ErrorEvent) => setMessage(event.message || 'Lỗi JavaScript không xác định')
    const onRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason
      setMessage(reason instanceof Error ? reason.message : String(reason))
    }
    window.addEventListener('error', onError)
    window.addEventListener('unhandledrejection', onRejection)
    return () => {
      window.removeEventListener('error', onError)
      window.removeEventListener('unhandledrejection', onRejection)
    }
  }, [])

  if (!message) return null
  return (
    <div role="alert" className="fixed top-0 inset-x-0 z-[100] flex items-center justify-between gap-4 bg-red-700 px-4 py-3 text-on-accent shadow-lg">
      <span>Lỗi ứng dụng: {message}</span>
      <button onClick={() => window.location.reload()} className="shrink-0 rounded border border-white/60 px-3 py-1 font-bold">Tải lại</button>
    </div>
  )
}

export default function App() {
  const { connectEvents, connectPoints } = useWsStore()
  
  useEffect(() => {
    connectEvents()
    connectPoints()
  }, [connectEvents, connectPoints])

  return (
    <ErrorBoundary>
      <GlobalErrorBanner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/control" replace />} />
          <Route path="/control" element={<ControlPage />} />
          <Route path="/wall" element={<WallPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
