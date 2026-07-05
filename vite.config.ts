import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    // The Flask backend (default http://localhost:5000) owns all
    // `/api/*` routes. We proxy them in dev so the frontend can use
    // relative URLs like `/api/auth/login` and `axios` can use
    // `withCredentials: true` against a same-origin URL.
    //
    // In production the same routing is handled by nginx (see
    // `nginx.conf`).
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        // Keep the `/api` prefix when forwarding to Flask.
        // Flask already has the `/api/auth/*` blueprint registered
        // with `url_prefix='/api/auth'`, so the path is correct.
        // secure: false,
      },
    },
  },
})
