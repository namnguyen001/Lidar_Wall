import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UiState {
  viewport: { x: number, y: number, zoom: number }
  setViewport: (vp: { x: number, y: number, zoom: number }) => void
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      viewport: { x: 0, y: 0, zoom: 1 },
      setViewport: (vp) => set({ viewport: vp }),
    }),
    { name: 'ui-store' }
  )
)
