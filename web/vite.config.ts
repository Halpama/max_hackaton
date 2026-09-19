import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const rootDir = path.dirname(fileURLToPath(import.meta.url))

/** Backend for the Vite proxy (phone → Mac:5173/api → this). */
const API_PROXY_TARGET = process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(rootDir, 'src'),
    },
  },
  optimizeDeps: {
    // MapLibre v6 worker breaks under Vite dep prebundling
    exclude: ['maplibre-gl'],
  },
  server: {
    // Listen on LAN so an iPhone on the same Wi‑Fi can open the app.
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      // Same-origin /api on the phone → local FastAPI (no CORS, no hardcoded IP).
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
      '/health': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: true,
    port: 4173,
    proxy: {
      '/api': { target: API_PROXY_TARGET, changeOrigin: true },
      '/health': { target: API_PROXY_TARGET, changeOrigin: true },
    },
  },
})
