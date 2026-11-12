import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0', port: 5173, strictPort: true,
      // Docker Desktop bind mounts on Windows do not reliably emit file events.
      watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === 'true', interval: 300 },
      proxy: {
        '/api': {
          target: process.env.API_PROXY_TARGET || env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: false,
          rewrite: (path: string) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
