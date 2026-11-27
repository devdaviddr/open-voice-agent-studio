/// <reference types="vitest/config" />
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
  server: {
    host: true,
    // File events do not cross Docker bind mounts on macOS; poll there (set in docker-compose.yml).
    watch: process.env.VITE_POLL ? { usePolling: true, interval: 300 } : undefined,
    proxy: {
      '/api': {
        target: process.env.OVAS_API_URL ?? 'http://localhost:8000',
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
      // Live sessions (WebSocket) go straight to the runtime.
      '/rt': {
        target: process.env.OVAS_RUNTIME_URL ?? 'http://localhost:8100',
        rewrite: (p) => p.replace(/^\/rt/, ''),
        ws: true,
      },
    },
  },
})
