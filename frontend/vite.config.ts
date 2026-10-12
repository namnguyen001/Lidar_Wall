import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: '/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://localhost:8080',
        changeOrigin: true
      },
      '/ws': {
        target: process.env.VITE_WS_TARGET ?? 'ws://localhost:8080',
        ws: true
      }
    }
  }
})
