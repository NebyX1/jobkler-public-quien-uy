import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { fileURLToPath } from 'node:url'

const projectRoot = path.dirname(fileURLToPath(import.meta.url))
const backendTarget = process.env.JOBKLER_API_TARGET || `http://127.0.0.1:${process.env.APP_PORT || '5000'}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(projectRoot, './src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: Number(process.env.VITE_PORT || '5173'),
    strictPort: true,
    // The Flask backend (default http://127.0.0.1:5000) owns all
    // `/api/*` routes. We proxy them in dev so the frontend can use
    // relative URLs like `/api/auth/login` and `axios` can use
    // `withCredentials: true` against a same-origin URL.
    //
    // In production the same routing is handled by nginx (see
    // `nginx.conf`).
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        // Keep the `/api` prefix when forwarding to Flask.
        // Flask already has the `/api/auth/*` blueprint registered
        // with `url_prefix='/api/auth'`, so the path is correct.
        // secure: false,
      },
    },
  },
  preview: {
    host: '127.0.0.1',
    port: Number(process.env.VITE_PORT || '4173'),
    strictPort: true,
  },
})
